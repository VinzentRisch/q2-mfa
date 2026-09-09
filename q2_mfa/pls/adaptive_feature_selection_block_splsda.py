# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
"""Adaptive block sPLS-DA feature-selection pipeline."""

import secrets

import pandas as pd
from rachis import Artifact, CategoricalMetadataColumn, Metadata, Visualization
from rachis.plugin import CaptureHolder
from rachis.plugin.context import IContext

from q2_mfa.pls.auto_keepx import adaptive_keepx_refinement
from q2_mfa.pls.feature_selection_block_splsda import _serialize_feature_selection
from q2_mfa.pls.types import PLSFeatureSelection, PLSFeatureSelectionDirFmt
from q2_mfa.pls.utils import _resolve_ncomp


def adaptive_feature_selection_block_splsda(
    ctx: IContext,
    tables: dict[str, Artifact],
    y: CategoricalMetadataColumn,
    design_matrix: Metadata = None,
    design_weight: float = None,
    tuned_ncomp: Artifact = None,
    ncomp: CaptureHolder[int] = None,
    keepx: dict = None,
    min_keepx: int = 5,
    max_keepx_fraction: float = 0.2,
    grid_size: int = 5,
    parallel_subgrids: int = 1,
    refinement_factor: float = 2.0,
    selection_rule: str = "one_se",
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
) -> tuple[Artifact, Visualization]:
    """
    Selects DIABLO features through adaptive coarse-to-fine keepX grids.

    Aligns the input tables and response once, then evaluates every unseen
    grid proposed by the adaptive controller through the registered private
    feature-selection action. Components are tuned sequentially, with selected
    values from earlier components supplied as ``already.tested.X``. All unique
    evaluations and the final selected counts are combined into one result and
    passed to the standard feature-selection visualizer.

    Args:
        ctx (Context): Pipeline execution context used to retrieve actions.
        tables (ResultCollection): Named feature-table artifacts used as
            blocks for block sPLS-DA (DIABLO).
        y (CategoricalMetadataColumn): Categorical response labels.
        design_matrix (Metadata, optional): Explicit block-relationship design
            matrix.
        design_weight (float, optional): Shared off-diagonal design weight.
        tuned_ncomp (Artifact, optional): Component-tuning artifact used when
            ``ncomp`` is not provided.
        ncomp (CaptureHolder[int], optional): Manual component count.
        keepx (dict, optional): Initial named keepX candidate grid. When
            omitted, the first grid is generated from the feature counts.
        min_keepx (int): Smallest automatically considered feature count.
        max_keepx_fraction (float): Initial upper-bound fraction per block.
        grid_size (int): Candidate count for initial and local grids.
        parallel_subgrids (int): Desired number of zero-repeat action subgrids
            for each refinement round.
        refinement_factor (float): Factor used to narrow or expand grids.
        selection_rule (str): Near-optimal candidate selection rule.
        scale (bool): Whether to standardize features within every block.
        tol (float): Convergence tolerance for the model fit.
        max_iter (int): Maximum iterative updates per model fit.
        near_zero_var (bool): Whether to remove near-zero variance features.
        validation (str): Cross-validation strategy accepted by mixOmics.
        folds (int): Number of M-fold cross-validation folds.
        nrepeat (int): Number of cross-validation repetitions.
        signif_threshold (float): Component improvement threshold.
        distance (str): Prediction distance used for classification.
        measure (str): Classification error measure used to select keepX.
        weighted (bool): Whether to use weighted rather than majority voting.
        seed (CaptureHolder[int], optional): Random seed shared by all grid
            evaluations.
        threads (int): Number of BiocParallel workers to use.

    Returns:
        tuple[Artifact, Visualization]: The combined adaptive feature-selection
            artifact and its diagnostic visualization.
    """
    align_samples = ctx.get_action("mfa", "_align_samples_metadata")
    select_features = ctx.get_action("mfa", "_feature_selection_block_splsda")
    visualise = ctx.get_action("mfa", "_feature_selection_block_splsda_visualiser")

    aligned_tables, aligned_metadata = align_samples(
        tables=tables,
        metadata_column=y,
    )
    aligned_y = aligned_metadata.view(Metadata).get_column(y.name)
    selected_ncomp = _resolve_ncomp(ncomp, tuned_ncomp, weighted, measure, distance)
    resolved_seed = CaptureHolder.get_or_set(seed, lambda: secrets.randbelow(2**31))
    feature_counts = {
        name: table.view(pd.DataFrame).shape[1]
        for name, table in aligned_tables.collection.items()
    }
    controller = adaptive_keepx_refinement(
        feature_counts,
        selected_ncomp,
        initial_keepx=keepx,
        min_keepx=min_keepx,
        max_keepx_fraction=max_keepx_fraction,
        grid_size=grid_size,
        parallel_subgrids=parallel_subgrids,
        refinement_factor=refinement_factor,
        selection_rule=selection_rule,
        nrepeat=nrepeat,
    )

    requests = next(controller)
    while True:
        grid_results = []
        for request in requests:
            (grid_result,) = select_features(
                tables=aligned_tables,
                y=aligned_y,
                keepx=_to_keepx_collection(request.keepx),
                already_tested_x=_to_keepx_collection(request.already_tested_keepx),
                design_matrix=design_matrix,
                design_weight=design_weight,
                ncomp=request.component,
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
                seed=resolved_seed,
                threads=threads,
            )
            grid_results.append(grid_result)
        error_rate_tables = tuple(
            grid_result.view(PLSFeatureSelectionDirFmt).error_rate.view(pd.DataFrame)
            for grid_result in grid_results
        )
        try:
            requests = controller.send(error_rate_tables)
        except StopIteration as completed:
            adaptive_result = completed.value
            break

    feature_selection = ctx.make_artifact(
        PLSFeatureSelection,
        _serialize_feature_selection(
            adaptive_result.error_rates,
            adaptive_result.selected_features,
        ),
    )
    (visualization,) = visualise(feature_selection=feature_selection)
    return feature_selection, visualization


def _to_keepx_collection(
    keepx: dict[str, list[int]] | None,
) -> dict[str, str] | None:
    """Converts parsed keepX values to QIIME collection strings."""
    if keepx is None:
        return None
    return {name: ",".join(map(str, values)) for name, values in keepx.items()}
