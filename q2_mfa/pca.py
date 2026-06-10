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

from q2_mfa.types import ComponentAnalysisDirFmt


def resolve_random_state(random_state: CaptureHolder[int], engine: str):
    if engine == "sklearn":
        return CaptureHolder.get_or_set(random_state, lambda: secrets.randbits(32))
    return CaptureHolder.get_or_set(random_state, lambda: None)


def drop_columns_with_missing_values(table: pd.DataFrame) -> pd.DataFrame:
    """
    Drop columns containing missing values from a table.

    Identifies columns with one or more missing values, emits a warning listing
    the removed column names, and returns the table with those columns removed.

    Args:
        table (pd.DataFrame): The input table to filter.

    Returns:
        pd.DataFrame: The table without columns that contain missing values.
    """
    missing_value_columns = table.columns[table.isna().any()]
    if len(missing_value_columns) > 0:
        warnings.warn(
            f"Dropped columns with missing values: {', '.join(missing_value_columns)}",
            UserWarning,
            stacklevel=2,
        )
        table = table.drop(columns=missing_value_columns)
    return table


def drop_zero_variance_columns(table: pd.DataFrame) -> pd.DataFrame:
    """
    Drop columns with zero variance from a table.

    Identifies columns whose values do not vary, emits a warning listing the
    removed column names, and returns the table with those columns removed.

    Args:
        table (pd.DataFrame): The input table to filter.

    Returns:
        pd.DataFrame: The table without zero-variance columns.
    """
    zero_variance_columns = table.columns[table.nunique(dropna=False) <= 1]
    if len(zero_variance_columns) > 0:
        warnings.warn(
            f"Dropped columns with zero variance: {', '.join(zero_variance_columns)}",
            UserWarning,
            stacklevel=2,
        )
        table = table.drop(columns=zero_variance_columns)
    return table


def pca(
    table: pd.DataFrame,
    rescale_with_mean: bool = True,
    rescale_with_std: bool = True,
    n_components: int = 2,
    n_iter: int = 3,
    random_state: CaptureHolder[int] = None,
    engine: str = "sklearn",
    filter_zero_variance: bool = True,
) -> ComponentAnalysisDirFmt:
    """
    Perform principal component analysis with prince.
    """
    table = drop_columns_with_missing_values(table)
    if filter_zero_variance:
        table = drop_zero_variance_columns(table)

    random_state = resolve_random_state(random_state, engine)

    pca_params = locals()
    pca_params.pop("table")
    pca_params.pop("filter_zero_variance")

    pca = prince.PCA(copy=True, check_input=True, **pca_params).fit(table)

    ordination = OrdinationResults(
        short_method_name="PCA",
        long_method_name="Principal Component Analysis",
        eigvals=pd.Series(pca.eigenvalues_),
        samples=pca.row_coordinates(table),
        features=pca.column_coordinates_,
        proportion_explained=pd.Series(pca.percentage_of_variance_),
    )

    results = ComponentAnalysisDirFmt()
    results.ordination.write_data(ordination, OrdinationResults)
    numeric_outputs = {
        results.sample_cosine_similarities: pca.row_cosine_similarities(table),
        results.sample_contributions: pca.row_contributions_,
        results.feature_correlations: pca.column_correlations,
        results.feature_contributions: pca.column_contributions_,
        results.feature_cosine_similarities: pca.column_cosine_similarities_,
    }
    for output, data in numeric_outputs.items():
        output.write_data(data, pd.DataFrame)

    return results
