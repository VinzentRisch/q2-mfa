# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
"""QIIME-facing DIABLO feature-selection actions and pipeline."""
import secrets

import pandas as pd
from q2templates.reports import matryoshka_template
from rachis import CategoricalMetadataColumn, Metadata
from rachis.plugin import CaptureHolder
from rpy2.robjects import IntVector, ListVector, r

from q2_mfa.pls.auto_keepx import adaptive_keepx_refinement
from q2_mfa.pls.types._format import PLSFeatureSelectionDirFmt
from q2_mfa.pls.types._tune_result import _PLSFeatureSelectionResult
from q2_mfa.pls.types._type import PLSFeatureSelection
from q2_mfa.pls.utils import (
    _align_samples,
    _build_bpparam,
    _expand_keepx_columns,
    _quiet_tune_block_splsda,
    _r_feature_selection_error_rate_to_dataframe,
    _resolve_design,
    _resolve_ncomp,
    _to_r_inputs,
)


def _feature_selection_block_splsda(
    tables: pd.DataFrame,
    y: CategoricalMetadataColumn,
    design_matrix: Metadata = None,
    design_weight: float | None = None,
    ncomp: int = 1,
    keepx: dict = None,
    previously_selected_keepx: dict | None = None,
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
) -> _PLSFeatureSelectionResult:
    """Runs one DIABLO keepX candidate grid for pipeline orchestration."""
    r("suppressPackageStartupMessages(library(mixOmics))")
    blocks, target = _align_samples(tables, y)
    design = _resolve_design(design_matrix, design_weight, list(blocks))
    resolved_seed = CaptureHolder.get_or_set(seed, lambda: secrets.randbelow(2**31))
    bpparam = _build_bpparam(threads, resolved_seed)
    if keepx is None:
        raise ValueError("keepx is required.")
    parsed_keepx = _parse_keepx_collection(keepx, list(blocks))
    previous = (
        _parse_keepx_collection(previously_selected_keepx, list(blocks))
        if previously_selected_keepx is not None
        else None
    )
    tune_result, feature_rates = _run_tune(
        blocks,
        target,
        design,
        ncomp,
        parsed_keepx,
        tol,
        max_iter,
        near_zero_var,
        scale,
        validation,
        folds,
        nrepeat,
        signif_threshold,
        distance,
        measure,
        weighted,
        resolved_seed,
        bpparam,
        previous,
    )
    selected_keepx = _selected_keepx(tune_result)
    return _PLSFeatureSelectionResult(
        error_rate=_wide_error_rates(feature_rates, tuple(blocks)),
        selected_features=_selected_features_table(selected_keepx),
    )


def feature_selection_block_splsda(
    ctx,
    tables,
    y,
    design_matrix=None,
    design_weight=None,
    tuned_components=None,
    ncomp=None,
    keepx=None,
    auto_keepx=True,
    min_keepx=5,
    max_keepx_fraction=0.2,
    grid_size=5,
    refinement_factor=2.0,
    selection_rule="one_se",
    ber_margin=0.0,
    se_multiplier=1.0,
    scale=True,
    tol=1e-6,
    max_iter=100,
    near_zero_var=False,
    validation="Mfold",
    folds=10,
    nrepeat=3,
    signif_threshold=0.01,
    distance="max.dist",
    measure="BER",
    weighted=True,
    seed=None,
    threads=1,
):
    """Runs manual or adaptive DIABLO keepX tuning and its diagnostics."""
    block_names = tuple(dict(tables.collection))
    selected_ncomp = _resolve_ncomp(
        ncomp, tuned_components, weighted, measure, distance
    )
    initial_keepx = _parse_keepx_collection(keepx, list(block_names)) if keepx else None
    select_features = ctx.get_action("mfa", "_feature_selection_block_splsda")

    def run_grid(component, grid, previous_keepx):
        previous = (
            {
                name: ",".join(map(str, values))
                for name, values in previous_keepx.items()
            }
            if previous_keepx
            else None
        )
        (tuning,) = select_features(
            tables=tables,
            y=y,
            design_matrix=design_matrix,
            design_weight=design_weight,
            ncomp=component,
            keepx={name: ",".join(map(str, values)) for name, values in grid.items()},
            previously_selected_keepx=previous,
            scale=scale,
            tol=tol,
            max_iter=max_iter,
            near_zero_var=near_zero_var,
            validation=validation,
            folds=folds,
            nrepeat=nrepeat,
            signif_threshold=signif_threshold,
            distance=distance,
            measure=measure,
            weighted=weighted,
            seed=seed,
            threads=threads,
        )
        table = tuning.view(PLSFeatureSelectionDirFmt).error_rate.view(pd.DataFrame)
        return _long_error_rates(table)

    if not auto_keepx:
        if initial_keepx is None:
            raise ValueError("keepx is required when auto_keepx is false.")
        (tuning,) = select_features(
            tables=tables,
            y=y,
            design_matrix=design_matrix,
            design_weight=design_weight,
            ncomp=selected_ncomp,
            keepx=keepx,
            scale=scale,
            tol=tol,
            max_iter=max_iter,
            near_zero_var=near_zero_var,
            validation=validation,
            folds=folds,
            nrepeat=nrepeat,
            signif_threshold=signif_threshold,
            distance=distance,
            measure=measure,
            weighted=weighted,
            seed=seed,
            threads=threads,
        )
    else:
        # Alignment remains in the refinement helper; grid evaluation crosses
        # the action boundary so every round is provenance-tracked.
        blocks, target = _align_samples(
            {
                name: artifact.view(pd.DataFrame)
                for name, artifact in tables.collection.items()
            },
            y,
        )
        design = _resolve_design(design_matrix, design_weight, list(blocks))
        automatic = adaptive_keepx_refinement(
            blocks,
            target,
            design,
            selected_ncomp,
            initial_keepx=initial_keepx,
            min_keepx=min_keepx,
            max_keepx_fraction=max_keepx_fraction,
            grid_size=grid_size,
            refinement_factor=refinement_factor,
            selection_rule=selection_rule,
            ber_margin=ber_margin,
            se_multiplier=se_multiplier,
            tol=tol,
            max_iter=max_iter,
            near_zero_var=near_zero_var,
            scale=scale,
            validation=validation,
            folds=folds,
            nrepeat=nrepeat,
            signif_threshold=signif_threshold,
            distance=distance,
            measure=measure,
            weighted=weighted,
            seed=seed,
            threads=threads,
            round_runner=run_grid,
        )
        cached = pd.concat(
            [
                _cache_to_error_rates(cache, component - 1)
                for component, cache in automatic.evaluation_cache.items()
            ],
            ignore_index=True,
        )
        tuning = ctx.make_artifact(
            PLSFeatureSelection,
            _PLSFeatureSelectionResult(
                error_rate=_wide_error_rates(cached, block_names),
                selected_features=_selected_features_table(automatic.keep_x),
            ),
        )
    return tuning, _feature_selection_visualization(ctx, tuning, block_names)


def _long_error_rates(error_rates: pd.DataFrame) -> pd.DataFrame:
    """Converts a serialized feature-selection error table to cache records."""
    keepx_columns = [column for column in error_rates if column.startswith("keepx_")]
    result = error_rates.melt(
        id_vars=["component", *keepx_columns],
        value_vars=["mean", "sd"],
        var_name="statistic",
        value_name="value",
    )
    result["keepx"] = (
        result[keepx_columns].astype(int).astype(str).agg("_".join, axis=1)
    )
    return result[["keepx", "component", "statistic", "value"]]


def _feature_selection_visualization(ctx, tuning, block_names):
    """Builds full-cache tabulation and optional two-block component heatmaps."""
    tabulate = ctx.get_action("metadata", "tabulate")
    error_rates = tuning.view(PLSFeatureSelectionDirFmt).error_rate.view(pd.DataFrame)
    (table,) = tabulate(input=Metadata(error_rates.set_index("id")))
    if len(block_names) != 2:
        return table
    heatmap = ctx.get_action("vizard", "heatmap")
    heatmaps = {}
    for component in sorted(error_rates["component"].unique()):
        component_rates = error_rates.loc[
            error_rates["component"] == component
        ].set_index("id")
        (plot,) = heatmap(
            metadata=Metadata(component_rates),
            x_measure=f"keepx_{block_names[0]}",
            y_measure=f"keepx_{block_names[1]}",
            gradient_measure="mean",
            title=f"sPLS-DA keepX error rates: component {component + 1}",
        )
        heatmaps[f"Component {component + 1}"] = plot
    heatmap_report = ctx.make_report(matryoshka_template, heatmaps)
    return ctx.make_report(
        matryoshka_template,
        {"Error-rate heatmaps": heatmap_report, "All error rates": table},
    )


def _parse_keepx_collection(
    keepx: dict, block_names: list[str]
) -> dict[str, list[int]]:
    """Parses a named collection of comma-separated candidate counts."""
    grid = dict(getattr(keepx, "collection", keepx))
    if set(grid) != set(block_names):
        raise ValueError("keepx keys must exactly match input block names.")
    parsed = {}
    for name in block_names:
        try:
            values = [int(value.strip()) for value in str(grid[name]).split(",")]
        except ValueError as error:
            raise ValueError(
                "Each keepx value must be a comma-separated list of positive integers."
            ) from error
        if not values or any(value < 1 for value in values):
            raise ValueError(
                "Each keepx value must be a comma-separated list of positive integers."
            )
        parsed[name] = values
    return parsed


def _cache_to_error_rates(cache, component: int) -> pd.DataFrame:
    """Converts cached component evaluations to long-form error-rate rows."""
    records = []
    for values, entry in cache.items():
        keepx = "_".join(map(str, values))
        records.extend(
            {
                "keepx": keepx,
                "component": component,
                "statistic": statistic,
                "value": entry[statistic],
            }
            for statistic in ("mean", "sd")
        )
    return pd.DataFrame(records, columns=["keepx", "component", "statistic", "value"])


def _selected_keepx(tune_result) -> dict[str, list[int]]:
    """Converts mixOmics' selected component-wise keepX values to Python."""
    values = tune_result.rx2("choice.keepX")
    return {
        str(name): [int(value) for value in block_values]
        for name, block_values in zip(values.names, values)
    }


def _selected_features_table(selected_keepx: dict[str, list[int]]) -> pd.DataFrame:
    """Converts component-wise selected keepX values to a wide table."""
    result = pd.DataFrame(selected_keepx)
    result.index.name = "component"
    return result


def _wide_error_rates(
    error_rates: pd.DataFrame, block_names: tuple[str, ...]
) -> pd.DataFrame:
    """Pivots mixOmics mean/SD error-rate rows into artifact table records."""
    expanded = _expand_keepx_columns(error_rates, block_names)
    keepx_columns = [f"keepx_{name}" for name in block_names]
    result = expanded.pivot(
        index=["component", *keepx_columns], columns="statistic", values="value"
    ).reset_index()
    result.insert(0, "id", [f"row{index}" for index in range(1, len(result) + 1)])
    return result[["id", "component", "mean", "sd", *keepx_columns]]


def _run_tune(
    blocks,
    target,
    design,
    ncomp,
    keep_x,
    tol,
    max_iter,
    near_zero_var,
    scale,
    validation,
    folds,
    nrepeat,
    signif_threshold,
    distance,
    measure,
    weighted,
    seed,
    bpparam,
    previously_selected_keepx=None,
):
    """Tunes DIABLO sparse variable counts for the requested components.

    Args:
        blocks: Aligned named feature blocks.
        target: Aligned categorical target.
        design: Validated DIABLO design matrix.
        ncomp: Number of components selected by perf.
        keep_x: Parsed candidate grids by block.
        tol: Convergence tolerance for tuning.
        max_iter: Maximum tuning iterations.
        near_zero_var: Whether to filter near-zero variance features.
        scale: Whether to scale blocks.
        validation: Cross-validation strategy.
        folds: Number of folds.
        nrepeat: Number of repeats.
        signif_threshold: Component improvement threshold.
        distance: Prediction distance used by tuning.
        measure: Error measure used by tuning.
        weighted: Whether to use weighted prediction performance.
        seed: Captured random seed.
        bpparam: R BiocParallel backend.

    Returns:
        tuple[object, pd.DataFrame]: R tuning result and its mean and standard
            deviation error rates by tested keepX combination.
    """
    print(
        "2. Tune number of retained features per block and component (keepX)\n",
        flush=True,
    )
    r_blocks, r_target, r_design = _to_r_inputs(blocks, target, design)
    r_keep_x = ListVector({name: IntVector(values) for name, values in keep_x.items()})
    parameters = {
        "ncomp": ncomp,
        "tol": tol,
        "max.iter": max_iter,
        "near.zero.var": near_zero_var,
        "design": r_design,
        "scale": scale,
        "test.keepX": r_keep_x,
        "validation": validation,
        "folds": folds,
        "nrepeat": nrepeat,
        "signif.threshold": signif_threshold,
        "dist": distance,
        "measure": measure,
        "weighted": weighted,
        "progressBar": False,
        "light.output": True,
        "BPPARAM": bpparam,
        "seed": seed,
    }
    if previously_selected_keepx:
        parameters["already.tested.X"] = ListVector(
            {
                name: IntVector(values)
                for name, values in previously_selected_keepx.items()
            }
        )
    tune_result = _quiet_tune_block_splsda(
        r_blocks,
        r_target,
        **parameters,
    )
    tuned_keep_x = tune_result.rx2("choice.keepX")
    keep_x_table = pd.DataFrame(
        {
            str(block_name): [int(value) for value in values]
            for block_name, values in zip(tuned_keep_x.names, tuned_keep_x)
        }
    )
    keep_x_table.index = [
        f"comp{component}" for component in range(1, len(keep_x_table) + 1)
    ]
    print("Tuned keepX values:\n", flush=True)
    print(f"{keep_x_table.to_string()}\n", flush=True)
    return tune_result, _r_feature_selection_error_rate_to_dataframe(tune_result)
