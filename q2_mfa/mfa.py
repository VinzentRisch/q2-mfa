# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import secrets
import warnings

import numpy as np
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
    table.index.name = "id"
    return table.reset_index()


def _flatten_partial_sample_coordinates(partial_coordinates):
    partial_coordinates = partial_coordinates.copy()
    partial_coordinates.columns = [
        f"{group}:{component}" for group, component in partial_coordinates.columns
    ]
    return _as_prince_wide_table(partial_coordinates)


def _compute_partial_axes_summary(mfa_result, table):
    """
    Compute correlations between each group component and each global component.

    Prince exposes the per-group PCA models used internally during MFA, but it
    does not expose this partial-axis summary as a fitted table.
    """
    global_scores = mfa_result.row_coordinates(table)
    rows = []

    for group, columns in mfa_result.groups_.items():
        group_scores = mfa_result[group].row_coordinates(table.loc[:, columns])
        for partial_component in group_scores.columns:
            for global_component in global_scores.columns:
                correlation = group_scores[partial_component].corr(
                    global_scores[global_component]
                )
                rows.append(
                    {
                        "group": group,
                        "partial_component": partial_component,
                        "global_component": global_component,
                        "correlation": (
                            0.0 if pd.isna(correlation) else float(correlation)
                        ),
                    }
                )

    return pd.DataFrame(rows)


def _compute_group_summary(mfa_result):
    """
    Compute group-level coordinates, contributions, and cos2 from Prince output.

    Prince exposes feature contributions and the internal per-group PCA models,
    but it does not expose this group-level summary as a fitted table.
    """
    eigenvalues = pd.Series(mfa_result.eigenvalues_)
    rows = []

    for group, columns in mfa_result.groups_.items():
        group_contribution = mfa_result.column_contributions_.loc[columns].sum(axis=0)
        first_eigenvalue = float(mfa_result[group].eigenvalues_[0])
        if first_eigenvalue <= 0:
            raise ValueError(
                f"Feature table '{group}' has a non-positive first eigenvalue."
            )

        group_dist2 = float(
            np.square(mfa_result[group].eigenvalues_ / first_eigenvalue).sum()
        )
        for component in group_contribution.index:
            contribution = float(group_contribution[component])
            coordinate = float(contribution * eigenvalues[component])
            rows.append(
                {
                    "group": group,
                    "component": component,
                    "coordinate": coordinate,
                    "contribution": contribution,
                    "cos2": float((coordinate**2) / group_dist2),
                }
            )

    return pd.DataFrame(rows)


def _to_ordination(mfa_result, table):
    return OrdinationResults(
        short_method_name="MFA",
        long_method_name="Multiple Factor Analysis",
        eigvals=pd.Series(mfa_result.eigenvalues_),
        samples=mfa_result.row_coordinates(table),
        features=mfa_result.column_coordinates_,
        proportion_explained=pd.Series(mfa_result.percentage_of_variance_),
    )


def _feature_cosine_similarities(mfa_result):
    coordinates = mfa_result.column_coordinates_
    squared_coordinates = coordinates.pow(2)
    squared_distance = squared_coordinates.sum(axis=1).replace(0, np.nan)
    return squared_coordinates.divide(squared_distance, axis=0).fillna(0.0)


def _create_mfa_results(
    ordination,
    partial_sample_coordinates,
    sample_cosine_similarities,
    partial_axes,
    group_summary,
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
    partial_axes.to_csv(results.path / "partial-axes.tsv", sep="\t", index=False)
    group_summary.to_csv(results.path / "group-summary.tsv", sep="\t", index=False)
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
    partial_sample_coordinates = _flatten_partial_sample_coordinates(
        mfa_result.partial_row_coordinates(table)
    )
    sample_cosine_similarities = _as_prince_wide_table(
        mfa_result.row_cosine_similarities(table)
    )
    partial_axes = _compute_partial_axes_summary(mfa_result, table)
    group_summary = _compute_group_summary(mfa_result)
    feature_correlations = _as_prince_wide_table(mfa_result.column_correlations)
    feature_contributions = _as_prince_wide_table(mfa_result.column_contributions_)
    feature_cosine_similarities = _as_prince_wide_table(
        _feature_cosine_similarities(mfa_result)
    )

    return _create_mfa_results(
        ordination,
        partial_sample_coordinates,
        sample_cosine_similarities,
        partial_axes,
        group_summary,
        feature_correlations,
        feature_contributions,
        feature_cosine_similarities,
    )
