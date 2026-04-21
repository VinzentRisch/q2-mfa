# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings

import pandas as pd
from q2_types.ordination import PCoAResults
from rachis.core.type import Properties
from skbio import OrdinationResults


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
            An artifact containing the global MFA ordination result.
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
        weighted_group = table.div(first_eigenvalue**0.5)
        weighted_group.columns = [
            f"{group_name}:{feature}" for feature in weighted_group.columns
        ]
        weighted_tables.append(weighted_group)

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

    # Recreate artifact with mfa property
    global_ordination = global_pca.view(OrdinationResults)
    mfa_results = ctx.make_artifact(PCoAResults % Properties("mfa"), global_ordination)

    return mfa_results
