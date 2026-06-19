# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from __future__ import annotations

import pandas as pd


class ComponentAnalysis:
    """
    Stores precomputed PCA or MFA output tables. Each public attribute is a pandas
    DataFrame in the same wide shape used by prince, including MultiIndex axes for
    MFA partial outputs where applicable.

    Args:
        sample_coordinates (pd.DataFrame): Sample coordinates by component.
        feature_coordinates (pd.DataFrame): Feature coordinates by component.
        eigenvalues (pd.Series): Numeric eigenvalues by component.
        percentage_of_variance (pd.Series): Percentage of variance by
            component, on Prince's 0-100 scale.
        cumulative_percentage_of_variance (pd.Series): Cumulative percentage of
            variance by component, on Prince's 0-100 scale.
        sample_cosine_similarities (pd.DataFrame): Sample cosine similarities.
        sample_contributions (pd.DataFrame): Sample contributions.
        feature_correlations (pd.DataFrame): Feature correlations.
        feature_contributions (pd.DataFrame): Feature contributions.
        feature_cosine_similarities (pd.DataFrame): Feature cosine similarities.
        partial_sample_coordinates (pd.DataFrame | None): MFA partial sample
            coordinates, if present.
        group_coordinates (pd.DataFrame | None): MFA group coordinates, if
            present.
        group_contributions (pd.DataFrame | None): MFA group contributions, if
            present.
        group_cosine_similarities (pd.DataFrame | None): MFA group cosine
            similarities, if present.
        partial_correlations (pd.DataFrame | None): MFA partial axis
            correlations, if present.
        partial_contributions (pd.DataFrame | None): MFA partial axis
            contributions, if present.

    Returns:
        None
    """

    def __init__(
        self,
        *,
        sample_coordinates: pd.DataFrame,
        feature_coordinates: pd.DataFrame,
        eigenvalues: pd.Series,
        percentage_of_variance: pd.Series,
        cumulative_percentage_of_variance: pd.Series,
        sample_cosine_similarities: pd.DataFrame,
        sample_contributions: pd.DataFrame,
        feature_correlations: pd.DataFrame,
        feature_contributions: pd.DataFrame,
        feature_cosine_similarities: pd.DataFrame,
        partial_sample_coordinates: pd.DataFrame | None = None,
        group_coordinates: pd.DataFrame | None = None,
        group_contributions: pd.DataFrame | None = None,
        group_cosine_similarities: pd.DataFrame | None = None,
        partial_correlations: pd.DataFrame | None = None,
        partial_contributions: pd.DataFrame | None = None,
    ):
        self.sample_coordinates = sample_coordinates.copy()
        self.feature_coordinates = feature_coordinates.copy()
        self.eigenvalues = eigenvalues.copy()
        self.percentage_of_variance = percentage_of_variance.copy()
        self.cumulative_percentage_of_variance = (
            cumulative_percentage_of_variance.copy()
        )
        self.sample_cosine_similarities = sample_cosine_similarities.copy()
        self.sample_contributions = sample_contributions.copy()
        self.feature_correlations = feature_correlations.copy()
        self.feature_contributions = feature_contributions.copy()
        self.feature_cosine_similarities = feature_cosine_similarities.copy()
        self.partial_sample_coordinates = _copy_optional(partial_sample_coordinates)
        self.group_coordinates = _copy_optional(group_coordinates)
        self.group_contributions = _copy_optional(group_contributions)
        self.group_cosine_similarities = _copy_optional(group_cosine_similarities)
        self.partial_correlations = _copy_optional(partial_correlations)
        self.partial_contributions = _copy_optional(partial_contributions)

    @property
    def is_mfa(self) -> bool:
        """
        Returns whether this result contains MFA-only output tables.

        Returns:
            bool: True when any MFA optional table is present.
        """
        return any(
            table is not None
            for table in (
                self.partial_sample_coordinates,
                self.group_coordinates,
                self.group_contributions,
                self.group_cosine_similarities,
                self.partial_correlations,
                self.partial_contributions,
            )
        )


def _copy_optional(table: pd.DataFrame | None) -> pd.DataFrame | None:
    """
    Copies an optional pandas object while preserving None values.

    Args:
        table (pd.DataFrame | None): The optional object to copy.

    Returns:
        pd.DataFrame | None: A copy of the input object, or None.
    """
    if table is None:
        return None
    return table.copy()
