# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import platform
import re

import numpy as np
import pandas as pd
from q2_types.feature_table import FeatureTable, Unconstrained
from q2_types.metadata import ImmutableMetadata
from rachis import Metadata, ResultCollection
from rachis.plugin import CaptureHolder
from rpy2.robjects import (
    IntVector,
    ListVector,
    StrVector,
    conversion,
    default_converter,
    pandas2ri,
    r,
)
from rpy2.robjects.conversion import localconverter


def _align_samples_metadata(ctx, tables, metadata_column):
    """Aligns feature tables and a metadata column to their shared samples."""
    filter_ids = ctx.get_action("feature_table", "filter_ids")
    metadata_column = metadata_column.drop_missing_values()
    shared_ids = metadata_column.get_ids()
    for table in tables.values():
        shared_ids.intersection_update(table.view(pd.DataFrame).index)
    if not shared_ids:
        raise ValueError("The feature tables and metadata column have no shared IDs.")
    shared_ids = [str(sample_id) for sample_id in shared_ids]
    metadata_column = metadata_column.filter_ids(shared_ids)
    aligned_metadata = Metadata(metadata_column.to_dataframe())
    sample_ids = aligned_metadata.to_dataframe().index.tolist()

    aligned_tables = {}
    for name, table in tables.items():
        (filtered_table,) = filter_ids(table=table, axis="sample", ids=shared_ids)
        aligned_tables[name] = ctx.make_artifact(
            FeatureTable[Unconstrained],
            filtered_table.view(pd.DataFrame).loc[sample_ids],
        )
    return (
        ResultCollection(aligned_tables),
        ctx.make_artifact(ImmutableMetadata, aligned_metadata),
    )


def _resolve_design(
    design_matrix, design_weight: float | None, block_names: list[str]
) -> pd.DataFrame | float:
    """Validates explicit design metadata or passes through a scalar design.

    Args:
        design_matrix: Optional Metadata-encoded matrix.
        design_weight (float | None): Scalar design weight for mixOmics.
        block_names (list[str]): Input-table collection keys.

    Returns:
        pd.DataFrame | float: Validated matrix or scalar weight for mixOmics.

    Raises:
        ValueError: If neither or both design representations are supplied, or
            explicit metadata is not a valid block design matrix.
    """
    if (design_matrix is None) == (design_weight is None):
        raise ValueError("Provide exactly one of 'design-matrix' or 'design-weight'.")
    if design_weight is not None:
        return design_weight

    matrix = design_matrix.to_dataframe().copy()
    expected = set(block_names)
    if set(matrix.index) != expected or set(matrix.columns) != expected:
        raise ValueError(
            "The row and column names in 'design-matrix' must exactly match "
            "feature-table collection names."
        )
    matrix = matrix.loc[block_names, block_names]
    try:
        matrix = matrix.astype(float)
    except (TypeError, ValueError) as error:
        raise ValueError("Values in 'design-matrix' must be numeric.") from error
    if not np.allclose(matrix.to_numpy(), matrix.to_numpy().T):
        raise ValueError("'design-matrix' must be symmetrical.")
    if not np.allclose(np.diag(matrix.to_numpy()), 0):
        raise ValueError("The diagonal of 'design-matrix' must contain only zeroes.")
    return matrix


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


def _resolve_ncomp(
    ncomp: CaptureHolder[int], tuned_ncomp, weighted, measure, distance
) -> int:
    """Captures a manual ncomp or derives it from a components artifact."""
    manual_ncomp = ncomp is not None and (
        not isinstance(ncomp, CaptureHolder) or ncomp.is_set
    )
    if manual_ncomp == (tuned_ncomp is not None):
        raise ValueError("Provide exactly one of ncomp or a tuned-ncomp artifact.")
    return CaptureHolder.get_or_set(
        ncomp,
        lambda: _ncomp_from_tuned_ncomp(tuned_ncomp, weighted, measure, distance),
    )


def _ncomp_from_tuned_ncomp(tuned_ncomp, weighted, measure, distance) -> int:
    """Reads the component count from the current tuning-artifact schema."""
    if tuned_ncomp is None:
        raise ValueError("Provide exactly one of ncomp or a tuned-ncomp artifact.")
    matrix_file = (
        tuned_ncomp.choice_matrix_weighted
        if weighted
        else tuned_ncomp.choice_matrix_majority
    )
    matrix = matrix_file.view(pd.DataFrame)
    requested_measure = "Overall.BER" if measure == "BER" else "Overall.ER"
    selected = matrix.loc[matrix["id"] == requested_measure, distance]
    if len(selected) != 1 or pd.isna(selected.iloc[0]):
        raise ValueError(
            "The component-tuning artifact has no selected number of components for "
            "the requested vote, measure, and distance."
        )
    return int(selected.iloc[0])


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
    """Reads selected keepX rows into the component-ordered parameter view."""
    if feature_selection is None:
        raise ValueError("Provide keepx or a feature-selection artifact.")
    table = feature_selection.selected_features.view(pd.DataFrame)
    expected = {
        (block, component) for block in block_names for component in range(ncomp)
    }
    records = {
        (str(row.block), int(row.component)): int(row.value)
        for row in table[["block", "component", "value"]].itertuples(index=False)
    }
    if set(records) != expected:
        raise ValueError(
            "The feature-selection artifact must contain one keepX value for "
            "each input block and fitted component."
        )
    return {
        f"component-{component + 1}": ",".join(
            str(records[(block, component)]) for block in block_names
        )
        for component in range(ncomp)
    }


def _build_bpparam(threads: int, seed: int):
    """Loads BiocParallel and creates an OS-appropriate backend.

    Args:
        threads (int): Requested workers, or 0 for BiocParallel's default.
        seed (int): Reproducible BiocParallel random-number seed.

    Returns:
        object: R SerialParam, SnowParam, or MulticoreParam backend.
    """
    r("suppressPackageStartupMessages(library(BiocParallel))")
    if threads == 1:
        return r["SerialParam"](**{"RNGseed": seed})
    kwargs = {"RNGseed": seed}
    if threads > 1:
        kwargs["workers"] = threads
    if platform.system() == "Windows":
        return r["SnowParam"](**{"type": "SOCK", **kwargs})
    return r["MulticoreParam"](**kwargs)


def _quiet_tune_block_splsda(*args, **kwargs):
    """Runs mixOmics tuning without its status output or warnings."""
    quiet_tune = r(
        "function(...) { "
        "output <- tempfile(); sink(output); "
        "on.exit({ sink(); unlink(output) }, add = TRUE); "
        "suppressWarnings(suppressMessages(tune.block.splsda(...))) "
        "}"
    )
    return quiet_tune(*args, **kwargs)


def _to_r_inputs(
    blocks,
    target,
    design,
    keep_x: dict[str, list[int]] | None = None,
    already_tested_x: dict[str, list[int]] | None = None,
):
    """Converts aligned pandas inputs to named R objects with preserved labels.

    Args:
        blocks: Named pandas input tables.
        target: Aligned categorical target series.
        design: Validated pandas design matrix.

    Returns:
        tuple: Named R block list, factor target, design matrix, and optional
            keepX lists.
    """
    with localconverter(default_converter + pandas2ri.converter):
        r_blocks = ListVector(
            {
                name: conversion.get_conversion().py2rpy(table)
                for name, table in blocks.items()
            }
        )
        r_design = conversion.get_conversion().py2rpy(design)
    r_target = r["factor"](StrVector(target.astype(str).tolist()))
    r_target.names = StrVector(target.index.astype(str).tolist())
    r_keep_x, r_already_tested_x = (
        (
            ListVector(
                {name: IntVector(values) for name, values in candidate_grid.items()}
            )
            if candidate_grid is not None
            else None
        )
        for candidate_grid in (keep_x, already_tested_x)
    )
    return r_blocks, r_target, r_design, r_keep_x, r_already_tested_x


def _r_named_frames(values) -> dict[str, pd.DataFrame]:
    """Converts a named R list of tables to a pandas mapping.

    Args:
        values: Named R list containing mixOmics table-like outputs.

    Returns:
        dict[str, pd.DataFrame]: Table name to pandas DataFrame mapping.
    """
    if type(values).__name__ == "NULLType":
        return {}
    try:
        names = list(values.names)
    except TypeError:
        return {}
    if not names:
        table = _r_to_dataframe(values)
        return {} if table is None else {"overall": table}
    return {str(name): _r_to_dataframe(value) for name, value in zip(names, values)}


def _r_ave_frames(values) -> dict[str, pd.DataFrame]:
    """Converts mixOmics AVE summaries into explicit component records.

    Args:
        values: Named R list containing AVE_X, AVE_outer, and AVE_inner.

    Returns:
        dict[str, pd.DataFrame]: AVE summary names mapped to already-long
            tables with block, component, and value columns as appropriate.
    """
    if type(values).__name__ == "NULLType":
        return {}
    ave_x = values.rx2("AVE_X")
    ave_x_frames = []
    for block_name, component_values in zip(ave_x.names, ave_x):
        values_array = np.asarray(component_values, dtype=float)
        ave_x_frames.append(
            pd.DataFrame(
                {
                    "block": str(block_name),
                    "component": np.arange(len(values_array)),
                    "value": values_array,
                }
            )
        )

    def component_vector(name: str) -> pd.DataFrame:
        component_values = np.asarray(values.rx2(name), dtype=float)
        return pd.DataFrame(
            {
                "component": np.arange(len(component_values)),
                "value": component_values,
            }
        )

    return {
        "AVE_X": pd.concat(ave_x_frames, ignore_index=True),
        "AVE_outer": component_vector("AVE_outer"),
        "AVE_inner": component_vector("AVE_inner"),
    }


def _r_criterion_to_dataframe(values) -> pd.DataFrame | None:
    """Flattens per-component convergence traces into one pandas table.

    Args:
        values: Unnamed R list of numeric convergence criteria, one per
            component.

    Returns:
        pd.DataFrame | None: Component, iteration, and criterion values, or
        None when mixOmics did not return convergence criteria.
    """
    if type(values).__name__ == "NULLType":
        return None
    traces = []
    for component, trace in enumerate(values):
        trace_values = np.asarray(trace, dtype=float)
        traces.append(
            pd.DataFrame(
                {
                    "component": component,
                    "iteration": np.arange(1, len(trace_values) + 1),
                    "criterion": trace_values,
                }
            )
        )
    return pd.concat(traces, ignore_index=True) if traces else None


def _r_feature_stability_to_dataframe(perf_result) -> pd.DataFrame | None:
    """Averages final-model selection frequencies across CV repeats.

    Args:
        perf_result: R ``perf`` result for the final block sPLS-DA model.

    Returns:
        pd.DataFrame | None: Block, feature, component, and mean selection
            frequency records, or None when mixOmics did not return stability.
    """
    stable = perf_result.rx2("features").rx2("stable")
    if type(stable).__name__ == "NULLType":
        return None
    records = []
    for repeat_values in stable:
        for block_name, component_values in zip(repeat_values.names, repeat_values):
            for component, selection_frequency in enumerate(component_values):
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
    if not records:
        return None
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
    for component, values in enumerate(auc):
        auc_table = pd.DataFrame(
            np.asarray(values),
            index=[str(name) for name in r["rownames"](values)],
            columns=[str(name) for name in r["colnames"](values)],
        )
        records.append(
            pd.DataFrame(
                {
                    "component": component,
                    "contrast": auc_table.index,
                    "auc": auc_table["AUC"].to_numpy(),
                    "p_value": auc_table["p-value"].to_numpy(),
                }
            )
        )
    return (
        pd.concat(records, ignore_index=True)
        if records
        else pd.DataFrame(columns=columns)
    )


def _r_vote_error_rate_to_dataframe(perf_result, vote: str) -> pd.DataFrame:
    """Converts a tuning vote's mean and standard-deviation error rates.

    Args:
        perf_result: R ``perf`` result for the final block sPLS-DA model.

    Returns:
        pd.DataFrame: Distance, class, component, mean, and standard deviation.
    """
    columns = ["distance", "class", "component", "mean", "sd"]
    records = {}
    for statistic, error_rates in (
        ("mean", perf_result.rx2(f"{vote}.error.rate")),
        ("sd", perf_result.rx2(f"{vote}.error.rate.sd")),
    ):
        if type(error_rates).__name__ == "NULLType":
            raise ValueError(
                f"mixOmics did not provide {statistic} error rates for {vote}."
            )
        for distance, rates in zip(error_rates.names, error_rates):
            values = np.asarray(rates, dtype=float)
            class_names = [str(name) for name in r["rownames"](rates)]
            for class_name, class_values in zip(class_names, values):
                for component, value in enumerate(class_values, start=1):
                    key = (str(distance), class_name, component)
                    record = records.setdefault(
                        key,
                        {"distance": key[0], "class": key[1], "component": key[2]},
                    )
                    record[statistic] = value
    error_rates = pd.DataFrame(records.values(), columns=columns)
    error_rates["component"] = error_rates["component"].astype("Int64")
    return error_rates


def _r_vote_error_rate_statistic_to_dataframe(
    error_rates, statistic: str, vote: str
) -> pd.DataFrame:
    """Converts one voting-scheme error-rate statistic to long-form records.

    Args:
        error_rates: Named R list of distance-specific error-rate matrices.
        statistic: Long-form statistic label, either ``mean`` or ``sd``.
        vote: mixOmics vote result prefix, such as ``WeightedVote``.

    Returns:
        pd.DataFrame: Vote, distance, class, component, statistic, and value
            records.
    """
    columns = ["vote", "distance", "class", "component", "statistic", "value"]
    if type(error_rates).__name__ == "NULLType":
        return pd.DataFrame(columns=columns)
    records = []
    for distance, rates in zip(error_rates.names, error_rates):
        values = np.asarray(rates, dtype=float)
        class_names = [str(name) for name in r["rownames"](rates)]
        for component in range(values.shape[1]):
            records.append(
                pd.DataFrame(
                    {
                        "vote": vote.removesuffix("Vote").lower(),
                        "distance": str(distance),
                        "class": class_names,
                        "component": component,
                        "statistic": statistic,
                        "value": values[:, component],
                    }
                )
            )
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
    """Calculates selected-feature correlations with their block variates.

    The calculation follows the feature coordinates used by mixOmics
    ``plotVar``: each selected feature is correlated with each fitted variate
    from its own block.
    """
    columns = ["block", "feature", "component", "value"]
    records = []
    for block, values in blocks.items():
        block_loadings = loadings[block]
        block_variates = variates[block]
        for component, loading_column in enumerate(block_loadings.columns):
            selected = block_loadings.index[
                block_loadings.iloc[:, component].fillna(0).ne(0)
            ]
            for feature in selected:
                paired = pd.concat(
                    [
                        values.loc[:, feature].rename("feature"),
                        block_variates.iloc[:, component].rename("variate"),
                    ],
                    axis=1,
                    join="inner",
                )
                records.append(
                    {
                        "block": block,
                        "feature": str(feature),
                        "component": component,
                        "value": paired["feature"].corr(paired["variate"]),
                    }
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
    columns = ["block_1", "feature_1", "block_2", "feature_2", "value"]
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
            "value": similarity[first, second],
        }
        for first in range(len(features))
        for second in range(first + 1, len(features))
    ]
    return pd.DataFrame.from_records(records, columns=columns)


def _r_feature_selection_error_rate_to_dataframe(tune_result) -> pd.DataFrame:
    """Converts tuning mean and SD error rates to long-form records.

    Args:
        tune_result: R ``tune.block.splsda`` result.

    Returns:
        pd.DataFrame: KeepX combination, component, statistic, and error-rate
            records.
    """
    columns = ["keepx", "component", "statistic", "value"]
    tables = [
        _r_feature_selection_error_rate_statistic_to_dataframe(
            tune_result.rx2("error.rate"), "mean"
        ),
        _r_feature_selection_error_rate_statistic_to_dataframe(
            tune_result.rx2("error.rate.sd"), "sd"
        ),
    ]
    tables = [table for table in tables if not table.empty]
    return (
        pd.concat(tables, ignore_index=True)
        if tables
        else pd.DataFrame(columns=columns)
    )


def _expand_keepx_columns(
    error_rates: pd.DataFrame, block_names: list[str] | tuple[str, ...]
) -> pd.DataFrame:
    """Replaces positional keepX labels with one named column per block."""
    block_names = tuple(block_names)
    expected = {"keepx", "component", "statistic", "value"}
    missing = expected.difference(error_rates.columns)
    if missing:
        raise ValueError(
            "Feature-selection error rates are missing required columns: "
            f"{', '.join(sorted(missing))}."
        )
    keepx_columns = [f"keepx_{name}" for name in block_names]
    parsed = error_rates["keepx"].map(
        lambda value: [int(count) for count in str(value).split("_")]
    )
    if any(len(values) != len(block_names) for values in parsed):
        raise ValueError(
            "Feature-selection keepX labels do not match the input block count."
        )
    result = error_rates.drop(columns="keepx").copy()
    result[keepx_columns] = pd.DataFrame(parsed.tolist(), index=result.index)
    return result[["component", "statistic", "value", *keepx_columns]]


def _r_feature_selection_error_rate_statistic_to_dataframe(
    error_rates, statistic: str
) -> pd.DataFrame:
    """Converts one tuning error-rate statistic matrix to long-form records.

    Args:
        error_rates: R matrix of tested keepX combinations by component.
        statistic: Long-form statistic label, either ``mean`` or ``sd``.

    Returns:
        pd.DataFrame: KeepX combination, component, statistic, and value
            records.
    """
    columns = ["keepx", "component", "statistic", "value"]
    if type(error_rates).__name__ == "NULLType":
        return pd.DataFrame(columns=columns)
    values = np.asarray(error_rates, dtype=float)
    keepx_values = [str(value) for value in r["dimnames"](error_rates)[0]]
    component_names = [str(value) for value in r["dimnames"](error_rates)[1]]
    component_numbers = []
    for position, name in enumerate(component_names):
        match = re.fullmatch(r"comp(\d+)", name)
        component_numbers.append(int(match.group(1)) - 1 if match else position)
    records = []
    for position, component in enumerate(component_numbers):
        records.append(
            pd.DataFrame(
                {
                    "keepx": keepx_values,
                    "component": component,
                    "statistic": statistic,
                    "value": values[:, position],
                }
            )
        )
    return (
        pd.concat(records, ignore_index=True)
        if records
        else pd.DataFrame(columns=columns)
    )


def _r_to_dataframe(value) -> pd.DataFrame | None:
    """Converts an R vector, matrix, or data frame while preserving labels."""
    if type(value).__name__ == "NULLType":
        return None
    row_names = r["rownames"](value)
    column_names = r["colnames"](value)
    value_names = r["names"](value)
    row_labels = (
        [str(label) for label in row_names]
        if type(row_names).__name__ != "NULLType"
        else None
    )
    column_labels = (
        [str(label) for label in column_names]
        if type(column_names).__name__ != "NULLType"
        else None
    )
    value_labels = (
        [str(label) for label in value_names]
        if type(value_names).__name__ != "NULLType"
        else None
    )
    with localconverter(default_converter + pandas2ri.converter):
        converted = conversion.rpy2py(value)
    if isinstance(converted, pd.DataFrame):
        if row_labels is not None and len(row_labels) == len(converted.index):
            converted.index = row_labels
        if column_labels is not None and len(column_labels) == len(converted.columns):
            converted.columns = column_labels
        return converted
    if isinstance(converted, pd.Series):
        if value_labels is not None and len(value_labels) == len(converted.index):
            converted.index = value_labels
        return converted.to_frame(name=converted.name or "value")
    array = np.asarray(converted)
    if array.ndim == 0:
        return pd.DataFrame({"value": [array.item()]})
    if array.ndim == 1:
        index = (
            value_labels if value_labels and len(value_labels) == len(array) else None
        )
        return pd.DataFrame({"value": array}, index=index)
    index = row_labels if row_labels and len(row_labels) == len(array) else None
    columns = (
        column_labels
        if column_labels and len(column_labels) == array.shape[1]
        else None
    )
    return pd.DataFrame(array, index=index, columns=columns)
