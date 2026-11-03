# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings

import numpy as np
import pandas as pd
from rachis.core.exceptions import RachisWarning
from rachis.plugin import CaptureHolder
from rpy2.robjects import (
    IntVector,
    ListVector,
    conversion,
    default_converter,
    pandas2ri,
    r,
)
from rpy2.robjects.conversion import localconverter
from rpy2.robjects.packages import importr
from rpy2.robjects.vectors import DataFrame as RDataFrame
from rpy2.robjects.vectors import FactorVector

from q2_mfa.pls.types._format import PLSComponentSelectionDirFmt

base = importr("base")
biocparallel = importr("BiocParallel")


def _align_samples(
    tables: dict[str, pd.DataFrame], target: pd.Series
) -> tuple[dict[str, pd.DataFrame], pd.Series]:
    """
    Aligns feature tables and a categorical response to shared samples.

    Drops missing response values, retains only sample IDs shared by every
    block and the response, and warns for each block or response row that is
    excluded.

    Args:
        tables (dict[str, pd.DataFrame]): Named feature tables indexed by
            sample ID.
        target (pd.Series): Categorical response values indexed by sample ID.

    Returns:
        tuple[dict[str, pd.DataFrame], pd.Series]: A tuple containing:
            - dict[str, pd.DataFrame]: Aligned named feature tables.
            - pd.Series: Aligned response values.

    Raises:
        ValueError: If fewer than two feature tables are supplied or no samples
            are shared by the feature tables and response.
    """
    if len(tables) < 2:
        raise ValueError("At least two named feature tables are required.")
    target = target.dropna()
    blocks = {**tables, "y": target.to_frame()}

    shared = next(iter(blocks.values())).index
    for table in list(blocks.values())[1:]:
        shared = shared.intersection(table.index)
    if shared.empty:
        raise ValueError("The input feature tables and response share no sample IDs.")

    aligned = {}
    for name, table in blocks.items():
        dropped = table.index.difference(shared)
        if not dropped.empty:
            warnings.warn(
                f"Dropping samples from block '{name}' that are not shared "
                f"across all blocks:\n"
                f"{', '.join(map(str, dropped))}",
                RachisWarning,
                stacklevel=2,
            )
        aligned[str(name)] = table.loc[shared].copy()
    target = aligned.pop("y").iloc[:, 0]
    return aligned, target


def _resolve_design(
    design_matrix: pd.DataFrame | None,
    design_weight: float | None,
    block_names: list[str],
) -> pd.DataFrame | float:
    if (design_matrix is None) == (design_weight is None):
        raise ValueError("Provide exactly one of 'design-matrix' or 'design-weight'.")
    if design_weight is not None:
        return design_weight

    expected = set(block_names)
    if set(design_matrix.index) != expected or set(design_matrix.columns) != expected:
        raise ValueError(
            "The row and column names in 'design-matrix' must exactly match "
            "the input feature-table collection names."
        )
    # reorder the matrix by block order
    design_matrix = design_matrix.loc[block_names, block_names]
    return design_matrix


def _build_bpparam(threads: int):
    """
    Creates a BiocParallel backend.

    Uses a serial backend for one worker and a multicore backend otherwise. A
    thread count of zero leaves worker selection to BiocParallel.

    Args:
        threads (int): Requested worker count, where zero selects the
            BiocParallel default.
    Returns:
        rpy2.robjects.RObject: Configured BiocParallel parameter object.
    """
    if threads == 1:
        return biocparallel.SerialParam()
    if threads > 1:
        return biocparallel.MulticoreParam(workers=threads)
    return biocparallel.MulticoreParam()


def _to_r_inputs(
    blocks: dict[str, pd.DataFrame],
    target: pd.Series,
    design: pd.DataFrame | float,
    keep_x: dict[str, list[int]] | None = None,
    already_tested_x: dict[str, list[int]] | None = None,
) -> tuple[
    ListVector, FactorVector, RDataFrame | float, ListVector | None, ListVector | None
]:
    """
    Converts aligned Python inputs to labelled R objects.

    Converts each block and an explicit design matrix through the pandas R
    converter, and creates a named R factor for the categorical response.

    Args:
        blocks (dict[str, pd.DataFrame]): Aligned named feature tables.
        target (pd.Series): Aligned categorical response values.
        design (pd.DataFrame | float): Explicit design matrix or scalar design
            weight.
        keep_x (dict, optional): Candidate keepX counts by block.
        already_tested_x (dict, optional): Selected keepX counts for prior
            components.

    Returns:
        tuple[rpy2.robjects.ListVector, rpy2.robjects.vectors.FactorVector,
        rpy2.robjects.RObject, ListVector | None, ListVector | None]: Named R
        blocks, response factor, design, and optional keepX and prior selections.
    """
    with localconverter(default_converter + pandas2ri.converter):
        converter = conversion.get_conversion()
        r_blocks = ListVector(
            {name: converter.py2rpy(table) for name, table in blocks.items()}
        )
        r_design = converter.py2rpy(design)
        r_target = converter.py2rpy(target)
    r_target = base.factor(r_target)
    r_keep_x, r_already_tested_x = (
        (
            ListVector({name: IntVector(values) for name, values in counts.items()})
            if counts is not None
            else None
        )
        for counts in (keep_x, already_tested_x)
    )
    return r_blocks, r_target, r_design, r_keep_x, r_already_tested_x


def _r_perf_error_rate_to_df(perf_result: ListVector, vote: str) -> pd.DataFrame:
    """
    Converts mixOmics vote error-rate means and standard deviations to rows.

    Combines the requested vote's error-rate and standard-deviation matrices
    into one table with distance measure, class, component, mean, and standard
    deviation columns.

    Args:
        perf_result (rpy2.robjects.vectors.ListVector): Result returned by
            mixOmics ``perf()``.
        vote (str): Vote type to extract, such as ``WeightedVote`` or
            ``MajorityVote``.

    Returns:
        pd.DataFrame: Error-rate records for the requested vote.
    """
    mean_error_rates = perf_result.rx2(f"{vote}.error.rate")
    sd_error_rates = perf_result.rx2(f"{vote}.error.rate.sd")
    tables = []

    for distance, mean_rates, sd_rates in zip(
        mean_error_rates.names, mean_error_rates, sd_error_rates
    ):
        means = np.asarray(mean_rates, dtype=float)
        standard_deviations = np.asarray(sd_rates, dtype=float)
        class_names = [str(name) for name in base.rownames(mean_rates)]
        component_count = means.shape[1]
        tables.append(
            pd.DataFrame(
                {
                    "distance": str(distance),
                    "class": np.repeat(class_names, component_count),
                    "component": np.tile(
                        np.arange(1, component_count + 1), len(class_names)
                    ),
                    "mean": means.ravel(),
                    "sd": standard_deviations.ravel(),
                }
            )
        )

    error_rates = pd.concat(tables, ignore_index=True)
    error_rates["component"] = error_rates["component"].astype("Int64")
    return error_rates


def _resolve_ncomp(
    ncomp: CaptureHolder[int],
    tuned_ncomp: PLSComponentSelectionDirFmt | None,
    weighted: bool,
    measure: str,
    distance: str,
) -> int:
    """
    Captures a manual component count or derives it from a tuning artifact.

    Uses a manually supplied ``ncomp`` when available; otherwise, reads the
    count selected by the requested voting, measure, and distance criteria from
    the component-tuning artifact. The resolved value is captured for action
    provenance.

    Args:
        ncomp (CaptureHolder[int] | int | None): Manually supplied component
            count or capture holder for the resolved value.
        tuned_ncomp (PLSComponentSelectionDirFmt | None): Component-tuning artifact
            used when no manual component count is supplied.
        weighted (bool): Whether to use the weighted rather than majority vote.
        measure (str): Requested prediction-error measure.
        distance (str): Requested prediction distance.

    Returns:
        int: The selected number of components.

    Raises:
        ValueError: If exactly one of a manual count and tuning artifact is not
            provided.
    """
    manual_ncomp = ncomp is not None and (
        not isinstance(ncomp, CaptureHolder) or ncomp.is_set
    )
    has_tuned_ncomp = tuned_ncomp is not None
    if manual_ncomp == has_tuned_ncomp:
        raise ValueError("Provide exactly one of ncomp or a tuned-ncomp artifact.")
    return CaptureHolder.get_or_set(
        ncomp,
        lambda: _ncomp_from_tuned_ncomp(tuned_ncomp, weighted, measure, distance),
    )


def _ncomp_from_tuned_ncomp(
    tuned_ncomp: PLSComponentSelectionDirFmt,
    weighted: bool,
    measure: str,
    distance: str,
) -> int:
    """
    Reads the component count chosen for a requested tuning criterion.

    Reads the weighted- or majority-vote choice matrix from the current
    component-tuning artifact.

    Args:
        tuned_ncomp (PLSComponentSelectionDirFmt): Component-tuning artifact
            containing the selected component counts.
        weighted (bool): Whether to use the weighted rather than majority vote.
        measure (str): Requested prediction-error measure.
        distance (str): Requested prediction distance.

    Returns:
        int: The uniquely selected number of components.
    """
    requested_measure = "Overall.BER" if measure == "BER" else "Overall.ER"
    matrix_file = (
        tuned_ncomp.choice_matrix_weighted
        if weighted
        else tuned_ncomp.choice_matrix_majority
    )
    matrix = matrix_file.view(pd.DataFrame)
    selected = matrix.loc[matrix["id"] == requested_measure, distance]
    if len(selected) != 1 or pd.isna(selected.iloc[0]):
        raise ValueError(
            "The component-tuning artifact has no selected number of components for "
            "the requested vote, measure, and distance."
        )
    return int(selected.iloc[0])


def _parse_fit_keepx(keepx, block_names: list[str], ncomp: int) -> dict[str, list[int]]:
    """Parses one comma-separated keepX string for each model component.

    Args:
        keepx: Collection of strings, ordered from component one onward.
        block_names (list[str]): Expected input-table collection keys.
        ncomp (int): Number of components in the final fitted model.

    Returns:
        dict[str, list[int]]: Final keepX values grouped by block.

    Raises:
        ValueError: If a component string is malformed or the collection does
            not provide one value per fitted component.
    """
    if keepx is None:
        raise ValueError("keepx is required for DIABLO feature selection.")
    collection = getattr(keepx, "collection", keepx)
    values = (
        list(collection.values()) if isinstance(collection, dict) else list(collection)
    )
    if len(values) != ncomp:
        raise ValueError(
            "keepx must provide one comma-separated value per component; "
            f"expected {ncomp}, received {len(values)}."
        )
    try:
        by_component = [
            [int(value.strip()) for value in str(component).split(",")]
            for component in values
        ]
    except ValueError as error:
        raise ValueError(
            "Each keepx component value must be a comma-separated integer list."
        ) from error
    if any(len(values) != len(block_names) for values in by_component):
        raise ValueError(
            "Each keepx component value must contain one count for every input "
            "block, in input collection order."
        )
    return {
        block: [component[index] for component in by_component]
        for index, block in enumerate(block_names)
    }


def _resolve_fit_keepx(
    keepx: CaptureHolder[dict], feature_selection, block_names: list[str], ncomp: int
) -> dict[str, list[int]]:
    """Captures manual keepX strings or derives them from feature selection."""
    manual_keepx = keepx is not None and (
        not isinstance(keepx, CaptureHolder) or keepx.is_set
    )
    if manual_keepx and feature_selection is not None:
        raise ValueError(
            "Provide either keepx or a feature-selection artifact, not both."
        )
    component_keepx = CaptureHolder.get_or_set(
        keepx,
        lambda: _component_keepx_from_feature_selection(
            feature_selection, block_names, ncomp
        ),
    )
    return _parse_fit_keepx(component_keepx, block_names, ncomp)


def _component_keepx_from_feature_selection(
    feature_selection, block_names: list[str], ncomp: int
) -> dict[str, str]:
    """Reads the wide keepX table into the component-ordered parameter view.

    Uses one-based component labels and orders each component's counts by the
    fitting action's input block order.
    """
    if feature_selection is None:
        raise ValueError("Provide keepx or a feature-selection artifact.")
    table = feature_selection.selected_features.view(pd.DataFrame)
    expected_components = list(range(1, ncomp + 1))
    if (
        set(table.columns) - {"id", "component"} != set(block_names)
        or table["component"].duplicated().any()
        or set(table["component"]) != set(expected_components)
    ):
        raise ValueError(
            "The feature-selection artifact must contain one keepX value for "
            "each input block and fitted component."
        )
    table = table.set_index("component").loc[expected_components, block_names]
    return {
        f"component-{component}": ",".join(str(int(value)) for value in row)
        for component, row in zip(expected_components, table.to_numpy())
    }


def _r_matrix_to_dataframe(values) -> pd.DataFrame:
    """Converts a labelled numeric R matrix while preserving row/column order."""
    return pd.DataFrame(
        np.asarray(values),
        index=[str(name) for name in values.rownames],
        columns=[str(name) for name in values.colnames],
    )


def _r_named_frames(values) -> dict[str, pd.DataFrame]:
    """Converts a named R list of labelled matrices to pandas tables."""
    return {
        str(name): _r_matrix_to_dataframe(value)
        for name, value in zip(values.names, values)
    }


def _component_vectors_to_dataframe(vectors, value_name: str) -> pd.DataFrame:
    """Flattens (block, numeric vector) pairs with one-based components.

    Component positions follow the order returned by mixOmics, including
    vectors without names such as AVE_outer and AVE_inner.
    """
    return pd.DataFrame.from_records(
        (
            (str(block), component, float(value))
            for block, values in vectors
            for component, value in enumerate(values, start=1)
        ),
        columns=["block", "component", value_name],
    )


def _r_ave_to_dataframe(values) -> pd.DataFrame:
    """Flattens block and overall AVE vectors into one labelled table."""
    ave_x = values.rx2("AVE_X")
    metrics = {
        "AVE_X": zip(ave_x.names, ave_x),
        "AVE_outer": [("overall", values.rx2("AVE_outer"))],
        "AVE_inner": [("overall", values.rx2("AVE_inner"))],
    }
    tables = []
    for metric, vectors in metrics.items():
        table = _component_vectors_to_dataframe(vectors, "value")
        table.insert(0, "metric", metric)
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def _r_criterion_to_dataframe(values) -> pd.DataFrame:
    """Flattens per-component convergence traces into one pandas table.

    Args:
        values: Unnamed R list of numeric convergence criteria, one per
            component.

    Returns:
        pd.DataFrame: Component, iteration, and criterion values.
    """
    return pd.DataFrame.from_records(
        (
            (component, iteration, float(criterion))
            for component, trace in enumerate(values, start=1)
            for iteration, criterion in enumerate(trace, start=1)
        ),
        columns=["component", "iteration", "criterion"],
    )


def _r_feature_stability_to_dataframe(perf_result) -> pd.DataFrame:
    """Averages final-model selection frequencies across CV repeats.

    Args:
        perf_result: R ``perf`` result for the final block sPLS-DA model.

    Returns:
        pd.DataFrame: Block, feature, component, and mean selection frequency.
    """
    stable = perf_result.rx2("features").rx2("stable")
    records = []
    for repeat_values in stable:
        for block_name, component_values in zip(repeat_values.names, repeat_values):
            for component, selection_frequency in enumerate(component_values, start=1):
                feature_names = [str(name) for name in r["names"](selection_frequency)]
                records.append(
                    pd.DataFrame(
                        {
                            "block": str(block_name),
                            "feature": feature_names,
                            "component": component,
                            "selection_frequency": np.asarray(
                                selection_frequency, dtype=float
                            ),
                        }
                    )
                )
    return (
        pd.concat(records, ignore_index=True)
        .groupby(["block", "feature", "component"], as_index=False)
        .selection_frequency.mean()
        .rename(columns={"selection_frequency": "mean_selection_frequency"})
    )


def _r_auc_to_dataframe(perf_result) -> pd.DataFrame:
    """Converts mixOmics per-component, per-contrast AUC results.

    Args:
        perf_result: R ``perf`` result for the final block sPLS-DA model.

    Returns:
        pd.DataFrame: Component, contrast, AUC, and p-value records.
    """
    auc = perf_result.rx2("auc")
    columns = ["component", "contrast", "auc", "p_value"]
    if type(auc).__name__ == "NULLType":
        return pd.DataFrame(columns=columns)
    records = []
    for component, values in enumerate(auc, start=1):
        auc_table = (
            _r_matrix_to_dataframe(values)
            .rename(columns={"AUC": "auc", "p-value": "p_value"})
            .rename_axis("contrast")
            .reset_index()
        )
        auc_table.insert(0, "component", component)
        records.append(auc_table[columns])
    return (
        pd.concat(records, ignore_index=True)
        if records
        else pd.DataFrame(columns=columns)
    )


def _feature_component_correlation_to_dataframe(
    blocks: dict[str, pd.DataFrame],
    variates: dict[str, pd.DataFrame],
    loadings: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Correlates features selected on any component with all block scores."""
    columns = ["block", "feature", "component", "correlation"]
    records = []
    for block, values in blocks.items():
        block_loadings = loadings[block]
        selected = block_loadings.index[block_loadings.fillna(0).ne(0).any(axis=1)]
        feature_values = values.loc[:, selected]
        for component, (_, scores) in enumerate(variates[block].items(), start=1):
            records.extend(
                (block, feature, component, feature_values[feature].corr(scores))
                for feature in selected
            )
    return pd.DataFrame.from_records(records, columns=columns)


def _r_feature_similarity_to_dataframe(
    model,
    blocks: dict[str, pd.DataFrame],
    loadings: dict[str, pd.DataFrame],
    ncomp: int,
) -> pd.DataFrame:
    """Captures the all-component similarity matrix returned by ``circosPlot``.

    mixOmics builds this matrix from feature-to-variate correlations, so its
    entries are component-derived similarities rather than raw feature
    correlations. Feature identities are reconstructed from the selected
    loading rows, in the ordering used by ``circosPlot``.
    """
    columns = ["block_1", "feature_1", "block_2", "feature_2", "similarity"]
    features = []
    for block in blocks:
        selected = loadings[block].index[
            loadings[block].iloc[:, :ncomp].abs().sum(axis=1).ne(0)
        ]
        features.extend((block, str(feature)) for feature in selected)
    if len(features) < 2:
        return pd.DataFrame(columns=columns)
    similarity = np.asarray(
        r["circosPlot"](model, comp=IntVector(range(1, ncomp + 1)), cutoff=0),
        dtype=float,
    )
    if similarity.shape != (len(features), len(features)):
        raise ValueError(
            "circosPlot returned a similarity matrix incompatible with the "
            "selected model features."
        )
    records = [
        {
            "block_1": features[first][0],
            "feature_1": features[first][1],
            "block_2": features[second][0],
            "feature_2": features[second][1],
            "similarity": similarity[first, second],
        }
        for first in range(len(features))
        for second in range(first + 1, len(features))
    ]
    return pd.DataFrame.from_records(records, columns=columns)
