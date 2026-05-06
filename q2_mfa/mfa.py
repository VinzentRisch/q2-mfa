# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import secrets
import warnings

import pandas as pd
import prince
from rachis.plugin import CaptureHolder
from skbio import OrdinationResults

from q2_mfa.types import MFAResultsDirFmt


def _build_prince_input(feature_tables):
    feature_tables = getattr(feature_tables, "collection", feature_tables)

    if len(feature_tables) < 2:
        raise ValueError("MFA requires at least two feature tables.")

    tables = {}
    consensus_samples = None
    for group_name, table in feature_tables.items():
        if ":" in group_name:
            raise ValueError("MFA group names cannot contain ':'.")

        tables[group_name] = table

        if consensus_samples is None:
            consensus_samples = table.index
        else:
            consensus_samples = consensus_samples.intersection(table.index)

    if consensus_samples.empty:
        raise ValueError("Feature tables do not share any sample IDs.")

    prefixed_tables = []
    groups = {}
    for group_name, table in tables.items():
        dropped_samples = table.index.difference(consensus_samples)
        if not dropped_samples.empty:
            warnings.warn(
                f"\n\033[93mDropping samples from group '{group_name}' that are not "
                f"shared across all tables:\n{', '.join(dropped_samples)}\033[0m",
                UserWarning,
            )

        table = table.loc[consensus_samples].copy()
        table.columns = [f"{group_name}:{feature}" for feature in table.columns]
        prefixed_tables.append(table)
        groups[group_name] = list(table.columns)

    return pd.concat(prefixed_tables, axis=1), groups


def _as_prince_wide_table(table):
    table = table.copy()
    if isinstance(table.index, pd.MultiIndex):
        table.index = [
            ":".join(str(value) for value in index_values)
            for index_values in table.index
        ]
    table.index.name = "id"
    table.columns = [str(index) for index in range(len(table.columns))]
    return table.reset_index()


def _to_ordination(mfa_result, table):
    return OrdinationResults(
        short_method_name="MFA",
        long_method_name="Multiple Factor Analysis",
        eigvals=pd.Series(mfa_result.eigenvalues_),
        samples=mfa_result.row_coordinates(table),
        features=mfa_result.column_coordinates_,
        proportion_explained=pd.Series(mfa_result.percentage_of_variance_),
    )


def _create_mfa_results(
    ordination,
    partial_sample_coordinates,
    sample_cosine_similarities,
    group_coordinates,
    group_contributions,
    group_cosine_similarities,
    partial_correlations,
    partial_contributions,
    feature_correlations,
    feature_contributions,
    feature_cosine_similarities,
):
    results = MFAResultsDirFmt()

    ordination.write(str(results.path / "ordination.txt"))
    partial_sample_coordinates.to_csv(
        results.path / "partial-sample-coordinates.tsv", sep="\t", index=False
    )
    sample_cosine_similarities.to_csv(
        results.path / "sample-cosine-similarities.tsv", sep="\t", index=False
    )
    group_coordinates.to_csv(
        results.path / "group-coordinates.tsv", sep="\t", index=False
    )
    group_contributions.to_csv(
        results.path / "group-contributions.tsv", sep="\t", index=False
    )
    group_cosine_similarities.to_csv(
        results.path / "group-cosine-similarities.tsv", sep="\t", index=False
    )
    partial_correlations.to_csv(
        results.path / "partial-correlations.tsv", sep="\t", index=False
    )
    partial_contributions.to_csv(
        results.path / "partial-contributions.tsv", sep="\t", index=False
    )
    feature_correlations.to_csv(
        results.path / "feature-correlations.tsv", sep="\t", index=False
    )
    feature_contributions.to_csv(
        results.path / "feature-contributions.tsv", sep="\t", index=False
    )
    feature_cosine_similarities.to_csv(
        results.path / "feature-cosine-similarities.tsv", sep="\t", index=False
    )

    return results


def mfa(
    feature_tables: pd.DataFrame,
    rescale_with_mean: bool = True,
    rescale_with_std: bool = True,
    n_components: int = 2,
    n_iter: int = 3,
    random_state: CaptureHolder[int] = None,
    engine: str = "sklearn",
) -> MFAResultsDirFmt:
    """
    Run Multiple Factor Analysis directly with prince.

    Parameters mirror the PCA action where applicable and are forwarded to
    ``prince.MFA``.
    """
    if engine == "sklearn":
        random_state = CaptureHolder.get_or_set(
            random_state, lambda: secrets.randbits(32)
        )
    else:
        random_state = CaptureHolder.get_or_set(random_state, lambda: None)

    table, groups = _build_prince_input(feature_tables)
    mfa_result = prince.MFA(
        rescale_with_mean=rescale_with_mean,
        rescale_with_std=rescale_with_std,
        n_components=n_components,
        n_iter=n_iter,
        copy=True,
        check_input=True,
        random_state=random_state,
        engine=engine,
    ).fit(table, groups=groups)

    ordination = _to_ordination(mfa_result, table)
    partial_sample_coordinates = _as_prince_wide_table(
        mfa_result.partial_row_coordinates(table)
    )
    sample_cosine_similarities = _as_prince_wide_table(
        mfa_result.row_cosine_similarities(table)
    )
    group_coordinates = _as_prince_wide_table(mfa_result.group_coordinates_)
    group_contributions = _as_prince_wide_table(mfa_result.group_contributions_)
    group_cosine_similarities = _as_prince_wide_table(
        mfa_result.group_cosine_similarities_
    )
    partial_correlations = _as_prince_wide_table(mfa_result.partial_correlations_)
    partial_contributions = _as_prince_wide_table(mfa_result.partial_contributions_)
    feature_correlations = _as_prince_wide_table(mfa_result.column_correlations)
    feature_contributions = _as_prince_wide_table(mfa_result.column_contributions_)
    feature_cosine_similarities = _as_prince_wide_table(
        mfa_result.column_cosine_similarities_
    )

    return _create_mfa_results(
        ordination,
        partial_sample_coordinates,
        sample_cosine_similarities,
        group_coordinates,
        group_contributions,
        group_cosine_similarities,
        partial_correlations,
        partial_contributions,
        feature_correlations,
        feature_contributions,
        feature_cosine_similarities,
    )
