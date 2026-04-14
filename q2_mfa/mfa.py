# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings
from collections import Counter

import pandas as pd
from q2_types.ordination import PCoAResults
from rachis.core.type import Properties
from skbio import OrdinationResults


def mfa(
    ctx,
    feature_tables,
    n_components=None,
    svd_solver="auto",
    tol=0.0,
    iterated_power="auto",
    n_oversamples=10,
    power_iteration_normalizer="auto",
    random_state=None,
):
    """
    Run Multiple Factor Analysis on a collection of feature tables.

    Each input table is analyzed with an exact one-component PCA to obtain the
    first eigenvalue used for classical MFA block weighting. The weighted tables
    are then concatenated and a global PCA is performed on the combined matrix
    using the user-specified PCA parameters.

    Parameters:
        ctx : qiime2.sdk.Context
            Plugin execution context used to access registered actions.
        feature_tables : Collection[FeatureTable[Unconstrained]]
            Collection of feature tables keyed by group name.

    Returns:
        qiime2.Artifact
            An artifact containing the global MFA ordination result.
    """
    global_pca_kwargs = {
        k: v for k, v in locals().items() if k not in {"ctx", "feature_tables"}
    }

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

    feature_name_counts = Counter()
    for _, table in tables.values():
        feature_name_counts.update(table.columns)

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
            table=table_artifact, n_components=1, svd_solver="full"
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
            (f"{feature}:{group_name}" if feature_name_counts[feature] > 1 else feature)
            for feature in weighted_group.columns
        ]
        weighted_tables.append(weighted_group)

    weighted_table_artifact = ctx.make_artifact(
        "FeatureTable[Unconstrained]", pd.concat(weighted_tables, axis=1)
    )

    # Run the global ordination on the weighted multi-block feature table.
    (global_pca,) = pca_action(
        table=weighted_table_artifact,
        **global_pca_kwargs,
    )

    # Recreate artifact with mfa property
    global_ordination = global_pca.view(OrdinationResults)
    mfa_results = ctx.make_artifact(PCoAResults % Properties("mfa"), global_ordination)

    return mfa_results
