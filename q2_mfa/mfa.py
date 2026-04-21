# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import tempfile
import warnings
from pathlib import Path

import pandas as pd
from skbio import OrdinationResults

from q2_mfa.types import MFAResults, MFAResultsDirFmt


def _compute_partial_sample_coordinates(group_results, global_ordination):
    """
    Compute MFA partial sample coordinates for each group and dimension.

    This returns the long-format table written to ``partial-scores.tsv`` with
    one row per sample, group, and retained global dimension.

    The implementation follows the partial factor score construction described
    in Abdi and Valentin (2007): for each group ``g``, the partial scores are
    computed from the group-specific cross-product matrix projected into the
    global MFA space,

    ``S_g = G * (Z_g Z_g^T) * P``

    where ``G`` is the number of groups and ``P`` is the global projection
    matrix. In the current scikit-learn PCA convention, the global projection
    matrix is reconstructed from the global sample scores and eigenvalues.
    This formulation was validated against ``FactoMineR::MFA`` up to the
    constant sample-score scaling difference between scikit-learn and
    FactoMineR.
    """
    n_groups = len(group_results)
    global_scores = global_ordination.samples
    eigvals = global_ordination.eigvals
    n_samples = len(global_scores.index)

    # Abdi (2007) defines the partial factor scores as
    #   S_g = G * (Z_g Z_g^T) * P
    # where G is the number of groups and P is the global projection matrix.
    #
    # In the current PCA implementation, the returned sample scores are the
    # sklearn scores T = U Σ and the reported eigenvalues are λ = Σ² / (n - 1).
    # Rewriting K P = T with K = X X^T gives the projection matrix in this
    # convention as P = T Σ⁻² = T / ((n - 1) * λ).
    projection = global_scores.divide((n_samples - 1) * eigvals, axis=1)
    partial_scores = []

    for group_result in group_results:
        weighted_table = group_result["weighted_table"]
        centered_group = weighted_table - weighted_table.mean(axis=0)
        group_cross_product = centered_group @ centered_group.T
        partial = pd.DataFrame(
            n_groups * (group_cross_product.to_numpy() @ projection.to_numpy()),
            index=group_cross_product.index,
            columns=range(1, projection.shape[1] + 1),
        )
        partial.index.name = "sample_id"
        partial = partial.reset_index().melt(
            id_vars="sample_id",
            var_name="dim",
            value_name="coordinate",
        )
        partial.insert(1, "group", group_result["group"])
        partial_scores.append(partial)

    return pd.concat(partial_scores, ignore_index=True)


def _compute_partial_axes_summary(group_results, global_ordination):
    """
    Compute the MFA partial-axes summary table.

    This returns the long-format table written to ``partial-axes.tsv`` with
    one row per group-specific axis and global MFA axis pair.

    The value reported here is the correlation between each group's local PCA
    sample scores and the global MFA sample scores. This matches the partial
    axes interpretation described in the Abdi MFA material, where block-specific
    axes are compared to the global axes through their alignment, and it also
    matches the ``FactoMineR::MFA`` partial-axes correlation output for the
    centered quantitative-group setup used by this pipeline.
    """
    global_scores = global_ordination.samples
    global_dims = list(global_scores.columns)
    rows = []

    for group_result in group_results:
        group_scores = group_result["ordination"].samples
        for partial_axis_idx, partial_axis in enumerate(group_scores.columns, start=1):
            for global_dim_idx, global_dim in enumerate(global_dims, start=1):
                value = group_scores[partial_axis].corr(global_scores[global_dim])
                rows.append(
                    {
                        "group": group_result["group"],
                        "partial_axis": partial_axis_idx,
                        "global_dim": global_dim_idx,
                        "value": 0.0 if pd.isna(value) else float(value),
                    }
                )

    return pd.DataFrame(rows)


def _compute_group_summary(group_results, global_ordination):
    """
    Compute the MFA group summary table.

    This returns the long-format table written to ``group-summary.tsv`` with
    one row per group and retained dimension. The table includes group
    coordinates, contributions, and ``cos2``, plus the block weighting terms
    retained during MFA construction.

    The implementation follows the active-group formulas used by
    ``FactoMineR::MFA``:

    - group contribution on a dimension is the sum of the feature
      contributions from that group on that dimension
    - group coordinate is ``contribution * global_eigenvalue``
    - group ``cos2`` is ``coordinate^2 / dist2_group``
    - ``dist2_group`` is the sum of squared normalized eigenvalues from the
      group's separate analysis

    This is intentionally based on the FactoMineR reference implementation,
    because these group-level summaries are not spelled out in the Abdi paper
    as directly as the partial individual scores are.
    """
    eigvals = global_ordination.eigvals
    feature_contrib = global_ordination.features.pow(2).multiply(eigvals, axis=1)
    total_by_dim = feature_contrib.sum(axis=0)
    rows = []

    for group_result in group_results:
        group = group_result["group"]
        weighted_columns = group_result["weighted_table"].columns
        group_contrib = feature_contrib.loc[weighted_columns].sum(axis=0) / total_by_dim
        group_dist2 = float(
            (group_result["ordination"].eigvals / group_result["first_eigenvalue"])
            .pow(2)
            .sum()
        )

        for dim_idx, dim_name in enumerate(group_contrib.index, start=1):
            contribution = float(group_contrib[dim_name])
            coordinate = float(contribution * eigvals[dim_name])
            rows.append(
                {
                    "group": group,
                    "dim": dim_idx,
                    "coordinate": coordinate,
                    "contribution": contribution,
                    "cos2": float((coordinate**2) / group_dist2),
                    "first_eigenvalue": float(group_result["first_eigenvalue"]),
                    "weight": float(group_result["weight"]),
                }
            )

    return pd.DataFrame(rows)


def _create_mfa_results_artifact(
    ctx,
    global_ordination,
    partial_scores,
    partial_axes,
    group_summary,
):
    """
    Build the composite ``MFAResults`` artifact from the computed MFA outputs.

    This helper writes the existing MFA directory-format payload:

    - ``ordination.txt``
    - ``partial-scores.tsv``
    - ``partial-axes.tsv``
    - ``group-summary.tsv``

    It does not implement MFA mathematics itself; it is only responsible for
    packaging the already computed outputs into the registered
    ``MFAResultsDirFmt`` so the pipeline can return the plugin's composite
    ``MFAResults`` semantic type.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        global_ordination.write(str(temp_dir / "ordination.txt"))
        partial_scores.to_csv(temp_dir / "partial-scores.tsv", sep="\t", index=False)
        partial_axes.to_csv(temp_dir / "partial-axes.tsv", sep="\t", index=False)
        group_summary.to_csv(temp_dir / "group-summary.tsv", sep="\t", index=False)
        return ctx.make_artifact(MFAResults, temp_dir, view_type=MFAResultsDirFmt)


def mfa(
    ctx,
    feature_tables,
    n_components=None,
    svd_solver="full",
    random_state=None,
):
    """
    Run Multiple Factor Analysis on a collection of feature tables.

    Each input table is analyzed with a PCA using the user-specified
    ``n_components``, ``svd_solver``, and ``random_state`` to obtain the first
    eigenvalue used for classical MFA block weighting. The weighted tables are
    then concatenated and a global PCA is performed on the combined matrix
    using the same PCA parameters.

    Parameters:
        ctx : qiime2.sdk.Context
            Plugin execution context used to access registered actions.
        feature_tables : Collection[FeatureTable[Unconstrained]]
            Collection of feature tables keyed by group name.
        n_components : int | None
            Number of components to keep for both the per-group and global
            PCAs, or ``None`` to keep all components.
        svd_solver : str
            SVD solver to use for both the per-group and global PCAs.
        random_state : int | None
            Random seed forwarded to PCA when using stochastic solvers.

    Returns:
        qiime2.Artifact
            An artifact containing the global MFA ordination result together
            with MFA-specific support tables.
    """
    pca_action = ctx.get_action("mfa", "pca")
    feature_tables = getattr(feature_tables, "collection", feature_tables)

    if len(feature_tables) < 2:
        raise ValueError("MFA requires at least two feature tables.")

    tables = {}
    consensus_samples = None

    # Find the shared sample IDs across all groups before any PCA is computed.
    for group_name, table_artifact in feature_tables.items():
        table = table_artifact.view(pd.DataFrame)
        tables[group_name] = (table_artifact, table)

        if consensus_samples is None:
            consensus_samples = table.index
        else:
            consensus_samples = consensus_samples.intersection(table.index)

    if consensus_samples.empty:
        raise ValueError("Feature tables do not share any sample IDs.")

    weighted_tables = []
    group_results = []

    # Subset every table to the consensus samples and warn about dropped rows.
    for group_name, (table_artifact, table) in tables.items():
        dropped_samples = table.index.difference(consensus_samples)
        if not dropped_samples.empty:
            warnings.warn(
                f"\n\033[93mDropping samples from group '{group_name}' that are not "
                f"shared across all tables:\n{', '.join(dropped_samples)}\033[0m",
                UserWarning,
            )

        table = table.loc[consensus_samples]

        table_artifact = ctx.make_artifact("FeatureTable[Unconstrained]", table)
        (group_pca,) = pca_action(
            table=table_artifact,
            n_components=n_components,
            svd_solver=svd_solver,
            random_state=random_state,
        )
        group_ordination = group_pca.view(OrdinationResults)
        first_eigenvalue = float(group_ordination.eigvals.iloc[0])

        if first_eigenvalue <= 0:
            raise ValueError(
                f"Feature table '{group_name}' has a non-positive first eigenvalue."
            )

        # Scale each group by the square root of its first eigenvalue.
        weight = first_eigenvalue**-0.5
        weighted_group = table * weight
        weighted_group.columns = [
            f"{group_name}:{feature}" for feature in weighted_group.columns
        ]
        weighted_tables.append(weighted_group)
        group_results.append(
            {
                "group": group_name,
                "first_eigenvalue": first_eigenvalue,
                "weight": weight,
                "ordination": group_ordination,
                "weighted_table": weighted_group,
            }
        )

    weighted_table_artifact = ctx.make_artifact(
        "FeatureTable[Unconstrained]", pd.concat(weighted_tables, axis=1)
    )

    # Run the global ordination on the weighted multi-block feature table.
    (global_pca,) = pca_action(
        table=weighted_table_artifact,
        n_components=n_components,
        svd_solver=svd_solver,
        random_state=random_state,
    )

    global_ordination = global_pca.view(OrdinationResults)
    partial_scores = _compute_partial_sample_coordinates(
        group_results, global_ordination
    )
    partial_axes = _compute_partial_axes_summary(group_results, global_ordination)
    group_summary = _compute_group_summary(group_results, global_ordination)
    mfa_results = _create_mfa_results_artifact(
        ctx,
        global_ordination,
        partial_scores,
        partial_axes,
        group_summary,
    )

    return mfa_results
