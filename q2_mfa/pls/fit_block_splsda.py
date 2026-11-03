# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
"""QIIME-facing DIABLO block sPLS-DA fitting action."""

import secrets

import numpy as np
import pandas as pd
from rachis import CategoricalMetadataColumn
from rachis.plugin import CaptureHolder
from rpy2.robjects import IntVector, r

from q2_mfa.pls.descriptions import fit_descriptions
from q2_mfa.pls.types._format import (
    PLSComponentSelectionDirFmt,
    PLSFeatureSelectionDirFmt,
    PLSFitDirFmt,
)
from q2_mfa.pls.utils import (
    _build_bpparam,
    _parse_keepx_collection,
    _r_perf_error_rate_to_df,
    _resolve_design,
    _resolve_ncomp,
    _to_r_inputs,
)


def fit_block_splsda(
    tables: pd.DataFrame,
    y: CategoricalMetadataColumn,
    design_matrix: pd.DataFrame = None,
    design_weight: float | None = None,
    tuned_components: PLSComponentSelectionDirFmt = None,
    ncomp: CaptureHolder[int] = None,
    keepx: CaptureHolder[dict] = None,
    feature_selection: PLSFeatureSelectionDirFmt = None,
    scale: bool = True,
    tol: float = 1e-6,
    max_iter: int = 100,
    near_zero_var: bool = False,
    validation: str = "Mfold",
    folds: int = 10,
    nrepeat: int = 3,
    signif_threshold: float = 0.01,
    distance: str = "max.dist",
    measure: str = "BER",
    weighted: bool = True,
    seed: CaptureHolder[int] = None,
    threads: int = 1,
) -> PLSFitDirFmt:
    """Fits DIABLO with supplied or previously selected components and keepX.

    ``ncomp`` and ``tuned_components`` are mutually exclusive. Likewise,
    provide manual block-keyed ``keepx`` strings or a feature-selection
    artifact, but not both. The input tables and response must already have
    identical sample IDs in the same order.
    """
    r("suppressPackageStartupMessages(library(mixOmics))")
    blocks = dict(tables.items())
    target = y.to_series()
    design = _resolve_design(design_matrix, design_weight, list(blocks))
    selected_ncomp = _resolve_ncomp(
        ncomp, tuned_components, weighted, measure, distance
    )
    selected_keepx = _resolve_fit_keepx(
        keepx, feature_selection, list(blocks), selected_ncomp
    )
    resolved_seed = CaptureHolder.get_or_set(seed, lambda: secrets.randbelow(2**31))
    bpparam = _build_bpparam(threads)

    r_blocks, r_target, r_design, r_keepx, _ = _to_r_inputs(
        blocks,
        target,
        design,
        keep_x=selected_keepx,
    )
    model = r["block.splsda"](
        r_blocks,
        r_target,
        **{
            "ncomp": selected_ncomp,
            "keepX": r_keepx,
            "design": r_design,
            "scale": scale,
            "tol": tol,
            "max.iter": max_iter,
            "near.zero.var": near_zero_var,
            "all.outputs": True,
            "verbose.call": False,
        },
    )
    perf_result = r["perf"](
        model,
        **{
            "dist": "all",
            "validation": validation,
            "folds": folds,
            "nrepeat": nrepeat,
            "signif.threshold": signif_threshold,
            "auc": True,
            "BPPARAM": bpparam,
            "seed": resolved_seed,
            "progressBar": False,
        },
    )
    return _serialize_fit(model, perf_result, blocks, selected_ncomp)


def _serialize_fit(
    model,
    perf_result,
    blocks,
    ncomp,
) -> PLSFitDirFmt:
    """Serializes final DIABLO model and performance outputs to JSONL files."""
    loadings = _r_named_frames(model.rx2("loadings"))
    variates = _r_named_frames(model.rx2("variates"))
    prop_expl_var = model.rx2("prop_expl_var")
    directory_format = PLSFitDirFmt()
    _write_fit_table(
        directory_format.loadings,
        _block_wide_values(loadings, "feature", "loading"),
        "loadings",
    )
    _write_fit_table(
        directory_format.variates,
        _block_wide_values(variates, "sample", "score"),
        "variates",
    )
    _write_fit_table(
        directory_format.prop_expl_var,
        _component_vectors_to_dataframe(
            zip(prop_expl_var.names, prop_expl_var),
            "proportion_explained_variance",
        ),
        "prop_expl_var",
    )
    _write_fit_table(
        directory_format.ave,
        _r_ave_to_dataframe(model.rx2("AVE")),
        "ave",
    )
    _write_fit_table(
        directory_format.crit,
        _r_criterion_to_dataframe(model.rx2("crit")),
        "crit",
    )
    _write_fit_table(
        directory_format.feature_stability,
        _r_feature_stability_to_dataframe(perf_result),
        "feature_stability",
    )
    _write_fit_table(directory_format.auc, _r_auc_to_dataframe(perf_result), "auc")
    _write_fit_table(
        directory_format.error_rate_weighted,
        _r_perf_error_rate_to_df(perf_result, "WeightedVote"),
        "error_rate_weighted",
    )
    _write_fit_table(
        directory_format.error_rate_majority,
        _r_perf_error_rate_to_df(perf_result, "MajorityVote"),
        "error_rate_majority",
    )
    _write_fit_table(
        directory_format.feature_component_correlation,
        _feature_component_correlation_to_dataframe(blocks, variates, loadings),
        "feature_component_correlation",
    )
    _write_fit_table(
        directory_format.feature_similarity,
        _r_feature_similarity_to_dataframe(model, blocks, loadings, ncomp),
        "feature_similarity",
    )
    return directory_format


def _write_fit_table(directory_file, table: pd.DataFrame, description_key: str) -> None:
    """Adds row IDs and a description, then writes the fit table."""
    ids = pd.array([str(index) for index in range(1, len(table) + 1)], dtype="string")
    table.insert(0, "id", ids)
    table.attrs["description"] = fit_descriptions[description_key]
    directory_file.write_data(table, pd.DataFrame)


def _block_wide_values(
    tables: dict[str, pd.DataFrame], identifier: str, value_name: str
) -> pd.DataFrame:
    """Converts named wide component tables into block-labelled records."""
    records = []
    for block, table in tables.items():
        working = table.copy()
        working.index.name = identifier
        working.columns = range(1, working.shape[1] + 1)
        long_table = working.reset_index().melt(
            id_vars=[identifier], var_name="component", value_name=value_name
        )
        long_table["component"] = long_table["component"].astype("int64")
        long_table.insert(0, "block", str(block))
        records.append(long_table)
    columns = ["block", identifier, "component", value_name]
    if not records:
        return pd.DataFrame(columns=columns)
    combined = pd.concat(records, ignore_index=True)[columns]
    combined[identifier] = combined[identifier].astype(str)
    return combined


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
    block_keepx = CaptureHolder.get_or_set(
        keepx,
        lambda: _block_keepx_from_feature_selection(
            feature_selection, block_names, ncomp
        ),
    )
    parsed = _parse_keepx_collection(block_keepx, block_names, ncomp)
    if any(len(counts) != ncomp for counts in parsed.values()):
        raise ValueError(
            f"Each keepx block must provide exactly {ncomp} feature counts, "
            "one for each fitted component."
        )
    return parsed


def _block_keepx_from_feature_selection(
    feature_selection, block_names: list[str], ncomp: int
) -> dict[str, str]:
    """Reads the wide keepX table into block-keyed parameter strings.

    Orders the counts within each block by one-based component label.
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
        block: ",".join(str(int(value)) for value in table[block])
        for block in block_names
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
