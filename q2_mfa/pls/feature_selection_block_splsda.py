# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import secrets

import pandas as pd
from rachis import CategoricalMetadataColumn, Metadata
from rachis.plugin import CaptureHolder
from rpy2.robjects import IntVector, ListVector, r

from q2_mfa.pls.types._format import PLSTuneComponentsDirFmt
from q2_mfa.pls.types._tune_result import _PLSFeatureSelectionResult
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


def feature_selection_block_splsda(
    tables: pd.DataFrame,
    y: CategoricalMetadataColumn,
    keepx: dict,
    design_matrix: Metadata = None,
    design_weight: float | None = None,
    tuned_components: PLSTuneComponentsDirFmt = None,
    ncomp: CaptureHolder[int] = None,
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
    """Tunes sparse DIABLO feature counts for selected components.

    Provide either ``ncomp`` or a tuned-components artifact. The chosen value
    is captured in the action provenance.
    """
    r("suppressPackageStartupMessages(library(mixOmics))")
    blocks, target = _align_samples(tables, y)
    design = _resolve_design(design_matrix, design_weight, list(blocks))
    resolved_seed = CaptureHolder.get_or_set(seed, lambda: secrets.randbelow(2**31))
    bpparam = _build_bpparam(threads, resolved_seed)

    selected_ncomp = _resolve_ncomp(
        ncomp, tuned_components, weighted, measure, distance
    )

    if keepx is None:
        raise ValueError("keepx is required for manual feature selection.")
    parsed_keepx = _parse_keepx_collection(keepx, list(blocks))
    tune_result, feature_rates = _run_tune(
        blocks,
        target,
        design,
        selected_ncomp,
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
    )
    selected_keepx = _selected_keepx(tune_result)
    return _PLSFeatureSelectionResult(
        error_rate=_expand_keepx_columns(feature_rates, tuple(blocks)),
        selected_features=_selected_features_table(selected_keepx),
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


def _selected_keepx(tune_result) -> dict[str, list[int]]:
    """Converts mixOmics' selected component-wise keepX values to Python."""
    values = tune_result.rx2("choice.keepX")
    return {
        str(name): [int(value) for value in block_values]
        for name, block_values in zip(values.names, values)
    }


def _selected_features_table(selected_keepx: dict[str, list[int]]) -> pd.DataFrame:
    """Serializes selected keepX values as block and zero-based component rows."""
    return pd.DataFrame(
        [
            {"block": block, "component": component, "value": value}
            for block, values in selected_keepx.items()
            for component, value in enumerate(values)
        ],
        columns=["block", "component", "value"],
    )


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
):
    """Tunes DIABLO sparse variable counts for the perf-selected components.

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
    tune_result = _quiet_tune_block_splsda(
        r_blocks,
        r_target,
        **{
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
        },
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
