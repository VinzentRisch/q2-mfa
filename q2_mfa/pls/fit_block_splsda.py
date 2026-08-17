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
from rachis import CategoricalMetadataColumn, Metadata
from rachis.plugin import CaptureHolder
from rpy2.robjects import IntVector, ListVector, r

from q2_mfa.pls.types._format import PLSFeatureSelectionDirFmt, PLSTuneComponentsDirFmt
from q2_mfa.pls.types._result import _PLSFitResult
from q2_mfa.pls.utils import (
    _align_samples,
    _build_bpparam,
    _feature_component_correlation_to_dataframe,
    _r_auc_to_dataframe,
    _r_ave_frames,
    _r_criterion_to_dataframe,
    _r_feature_similarity_to_dataframe,
    _r_feature_stability_to_dataframe,
    _r_named_frames,
    _r_vote_error_rate_to_dataframe,
    _resolve_design,
    _resolve_fit_keepx,
    _resolve_ncomp,
    _to_r_inputs,
)


def fit_block_splsda(
    tables: pd.DataFrame,
    y: CategoricalMetadataColumn,
    design_matrix: Metadata = None,
    design_weight: float | None = None,
    tuned_components: PLSTuneComponentsDirFmt = None,
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
) -> _PLSFitResult:
    """Fits DIABLO with supplied or previously selected components and keepX.

    ``ncomp`` and ``tuned_components`` are mutually exclusive. Likewise,
    provide manual component-ordered ``keepx`` strings or a feature-selection
    artifact, but not both.
    """
    r("suppressPackageStartupMessages(library(mixOmics))")
    blocks, target = _align_samples(tables, y)
    design = _resolve_design(design_matrix, design_weight, list(blocks))
    selected_ncomp = _resolve_ncomp(
        ncomp, tuned_components, weighted, measure, distance
    )
    selected_keepx = _resolve_fit_keepx(
        keepx, feature_selection, list(blocks), selected_ncomp
    )
    resolved_seed = CaptureHolder.get_or_set(seed, lambda: secrets.randbelow(2**31))
    bpparam = _build_bpparam(threads, resolved_seed)

    model = _fit_model(
        blocks,
        target,
        design,
        selected_ncomp,
        selected_keepx,
        scale,
        tol,
        max_iter,
        near_zero_var,
    )
    perf_result = _run_final_perf(
        model, validation, folds, nrepeat, signif_threshold, resolved_seed, bpparam
    )
    return _to_pls_fit_result(model, perf_result, blocks, selected_ncomp)


def _fit_model(
    blocks, target, design, ncomp, keepx, scale, tol, max_iter, near_zero_var
):
    """Calls mixOmics block.splsda with final selected values."""
    r_blocks, r_target, r_design = _to_r_inputs(blocks, target, design)
    r_keepx = ListVector({name: IntVector(values) for name, values in keepx.items()})
    return r["block.splsda"](
        r_blocks,
        r_target,
        **{
            "ncomp": ncomp,
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


def _run_final_perf(model, validation, folds, nrepeat, signif_threshold, seed, bpparam):
    """Runs the post-fit mixOmics performance assessment."""
    return r["perf"](
        model,
        **{
            "dist": "all",
            "validation": validation,
            "folds": folds,
            "nrepeat": nrepeat,
            "signif.threshold": signif_threshold,
            "auc": True,
            "BPPARAM": bpparam,
            "seed": seed,
            "progressBar": False,
        },
    )


def _to_pls_fit_result(model, perf_result, blocks, ncomp) -> _PLSFitResult:
    """Converts final model and post-fit perf outputs to artifact tables."""
    loadings = _r_named_frames(model.rx2("loadings"))
    variates = _r_named_frames(model.rx2("variates"))
    return _PLSFitResult(
        loadings=loadings,
        loadings_star=_r_named_frames(model.rx2("loadings.star")),
        variates=variates,
        prop_expl_var=_r_named_frames(model.rx2("prop_expl_var")),
        vip={},
        ave=_r_ave_frames(model.rx2("AVE")),
        crit=_r_criterion_to_dataframe(model.rx2("crit")),
        feature_stability=_r_feature_stability_to_dataframe(perf_result),
        auc=_r_auc_to_dataframe(perf_result),
        error_rate=pd.concat(
            [
                _r_vote_error_rate_to_dataframe(perf_result, "WeightedVote"),
                _r_vote_error_rate_to_dataframe(perf_result, "MajorityVote"),
            ],
            ignore_index=True,
        ),
        feature_component_correlation=_feature_component_correlation_to_dataframe(
            blocks, variates, loadings
        ),
        feature_similarity=_r_feature_similarity_to_dataframe(
            model, blocks, loadings, ncomp
        ),
    )
