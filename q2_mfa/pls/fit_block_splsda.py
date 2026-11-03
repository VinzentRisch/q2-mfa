# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
"""QIIME-facing DIABLO block sPLS-DA fitting action."""

import secrets

import pandas as pd
from rachis import CategoricalMetadataColumn
from rachis.plugin import CaptureHolder
from rpy2.robjects import r

from q2_mfa.pls.descriptions import fit_descriptions
from q2_mfa.pls.types._format import (
    PLSComponentSelectionDirFmt,
    PLSFeatureSelectionDirFmt,
    PLSFitDirFmt,
)
from q2_mfa.pls.utils import (
    _build_bpparam,
    _feature_component_correlation_to_dataframe,
    _r_auc_to_dataframe,
    _r_ave_frames,
    _r_criterion_to_dataframe,
    _r_feature_similarity_to_dataframe,
    _r_feature_stability_to_dataframe,
    _r_named_frames,
    _r_perf_error_rate_to_df,
    _resolve_design,
    _resolve_fit_keepx,
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
    provide manual component-ordered ``keepx`` strings or a feature-selection
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
    directory_format = PLSFitDirFmt()
    _write_fit_table(
        directory_format.loadings,
        _block_wide_values(loadings, "feature"),
        "loadings",
    )
    _write_optional_fit_table(
        directory_format.loadings_star,
        _block_wide_values(_r_named_frames(model.rx2("loadings.star")), "feature"),
        "loadings_star",
    )
    _write_fit_table(
        directory_format.variates,
        _block_wide_values(variates, "sample"),
        "variates",
    )
    _write_fit_table(
        directory_format.prop_expl_var,
        _block_component_values(_r_named_frames(model.rx2("prop_expl_var"))),
        "prop_expl_var",
    )
    _write_optional_fit_table(directory_format.vip, pd.DataFrame(), "vip")
    _write_optional_fit_table(
        directory_format.ave,
        _ave_values(_r_ave_frames(model.rx2("AVE"))),
        "ave",
    )
    _write_optional_fit_table(
        directory_format.crit,
        _r_criterion_to_dataframe(model.rx2("crit")),
        "crit",
    )
    _write_optional_fit_table(
        directory_format.feature_stability,
        _r_feature_stability_to_dataframe(perf_result),
        "feature_stability",
    )
    _write_fit_table(directory_format.auc, _r_auc_to_dataframe(perf_result), "auc")
    _write_error_rate_table(
        directory_format.error_rate_weighted,
        _r_perf_error_rate_to_df(perf_result, "WeightedVote"),
        "error_rate_weighted",
    )
    _write_error_rate_table(
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
    """Attaches a JSONL description and writes a required fit-result table."""
    table = table.convert_dtypes()
    table.attrs["description"] = fit_descriptions[description_key]
    directory_file.write_data(table, pd.DataFrame)


def _write_optional_fit_table(
    directory_file, table: pd.DataFrame | None, description_key: str
) -> None:
    """Writes an optional fit-result table only when it contains records."""
    if table is not None and not table.empty:
        _write_fit_table(directory_file, table, description_key)


def _write_error_rate_table(
    directory_file, error_rate: pd.DataFrame, description_key: str
) -> None:
    """Adds stable IDs and writes one voting scheme's fit error rates."""
    error_rate = error_rate.copy()
    error_rate.insert(
        0, "id", [f"row{index}" for index in range(1, len(error_rate) + 1)]
    )
    _write_fit_table(directory_file, error_rate, description_key)


def _block_wide_values(
    tables: dict[str, pd.DataFrame], identifier: str
) -> pd.DataFrame:
    """Converts named wide component tables into block-labelled records."""
    records = []
    for block, table in tables.items():
        working = table.copy()
        working.index.name = identifier
        long_table = working.reset_index().melt(
            id_vars=[identifier], var_name="component", value_name="value"
        )
        long_table["component"] = [
            component
            for component in range(1, working.shape[1] + 1)
            for _ in range(len(working))
        ]
        long_table.insert(0, "block", str(block))
        records.append(long_table)
    columns = ["block", identifier, "component", "value"]
    if not records:
        return pd.DataFrame(columns=columns)
    combined = pd.concat(records, ignore_index=True)[columns]
    combined[identifier] = combined[identifier].astype(str)
    return combined


def _block_component_values(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Consolidates per-block explained-variance vectors by component."""
    records = []
    for block, table in tables.items():
        working = table.copy()
        if working.shape[1] == 1:
            long_table = pd.DataFrame(
                {"component": working.index, "value": working.iloc[:, 0]}
            )
        elif working.shape[0] == 1:
            long_table = pd.DataFrame(
                {"component": working.columns, "value": working.iloc[0]}
            )
        else:
            raise ValueError(
                "mixOmics prop_expl_var must contain one value per component."
            )
        long_table["component"] = range(1, len(long_table) + 1)
        long_table.insert(0, "block", str(block))
        records.append(long_table)
    columns = ["block", "component", "value"]
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.concat(records, ignore_index=True)[columns]


def _ave_values(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Consolidates AVE metrics while retaining their metric and block labels."""
    records = []
    for metric, table in tables.items():
        working = table.copy()
        if "block" not in working:
            working.insert(0, "block", "overall")
        working.insert(0, "metric", metric)
        records.append(working[["metric", "block", "component", "value"]])
    columns = ["metric", "block", "component", "value"]
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.concat(records, ignore_index=True)[columns]
