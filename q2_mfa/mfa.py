# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings
from functools import reduce

import pandas as pd
import prince
from rachis import Metadata
from rachis.plugin import CaptureHolder
from skbio import OrdinationResults

from q2_mfa.pca import (
    drop_columns_with_missing_values,
    drop_zero_variance_columns,
    resolve_random_state,
)
from q2_mfa.types import ComponentAnalysisDirFmt


def _validate_group_name(group_name):
    """
    Checks that the group name does not contain the colon character, which is
    reserved for constructing prefixed MFA feature names in the form
    ``group:feature``.
    """
    if ":" in group_name:
        raise ValueError("MFA group names cannot contain ':'.")


def _parse_metadata_groups(metadata_groups, metadata_columns):
    """
    Resolves metadata group specifications into group-to-column mappings.

    Converts optional metadata group input into a dictionary where keys are MFA
    group names and values are lists of metadata column names. If no mapping is
    provided, all metadata columns are assigned to the default ``metadata``
    group. If a string is provided, all metadata columns are assigned to a group
    with that string as its name. If a mapping is provided, its keys are group
    names and its comma-separated string values are parsed as metadata columns.

    Args:
        metadata_groups (str | dict | None): The metadata group specification.
        metadata_columns (Iterable[str]): The available metadata column names.

    Returns:
        dict: Metadata group names mapped to lists of metadata column names.
    """
    if metadata_groups is None:
        return {"metadata": list(metadata_columns)}

    if isinstance(metadata_groups, str):
        metadata_groups = metadata_groups.strip()
        if not metadata_groups:
            raise ValueError("Metadata group mapping cannot be empty.")
        return {metadata_groups: list(metadata_columns)}

    group_mapping = {}
    for group_name, columns in metadata_groups.items():
        if not group_name:
            raise ValueError("Metadata group names cannot be empty.")
        columns = [column.strip() for column in columns.split(",") if column.strip()]
        if not columns:
            raise ValueError(
                f"Metadata group '{group_name}' must contain at least one column."
            )
        group_mapping[group_name] = columns
    return group_mapping


def _metadata_to_grouped_tables(sample_metadata, metadata_groups):
    """
    Converts sample metadata into per-group DataFrames for MFA.

    Converts a metadata object to a DataFrame and splits it into one
    DataFrame per requested metadata group. The function validates that all
    requested metadata columns exist, that no metadata column is assigned to
    more than one metadata group, and that metadata group names can be used as
    MFA group names.

    Args:
        sample_metadata (Metadata | None): The sample metadata to include in
            the MFA input.
        metadata_groups (str | dict | None): The metadata group specification.

    Returns:
        dict: Metadata group names mapped to DataFrames containing the selected
            metadata columns.
    """
    if sample_metadata is None:
        if metadata_groups is not None:
            raise ValueError("metadata_groups requires sample_metadata.")
        return {}

    metadata = sample_metadata.to_dataframe().copy()
    group_mapping = _parse_metadata_groups(metadata_groups, metadata.columns)
    missing_columns = sorted(
        {
            column
            for columns in group_mapping.values()
            for column in columns
            if column not in metadata.columns
        }
    )
    if missing_columns:
        raise ValueError(
            "Metadata group mapping references columns not present in the metadata: "
            f"{', '.join(missing_columns)}"
        )

    duplicated_columns = sorted(
        {
            column
            for columns in group_mapping.values()
            for column in columns
            if sum(column in group for group in group_mapping.values()) > 1
        }
    )
    if duplicated_columns:
        raise ValueError(
            "Metadata columns cannot be assigned to multiple groups: "
            f"{', '.join(duplicated_columns)}"
        )

    grouped_tables = {}
    for group_name, columns in group_mapping.items():
        _validate_group_name(group_name)
        grouped_tables[group_name] = metadata.loc[:, columns]

    return grouped_tables


def _build_prince_input(
    tables: dict = None,
    sample_metadata=None,
    metadata_groups=None,
    filter_zero_variance: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """
    Builds the wide input table and group mapping expected by ``prince.MFA``.

    Merges feature-table groups and metadata groups, keeps only sample IDs that
    are shared across every group, and prefixes each column as
    ``group:feature``. The returned group mapping tells Prince which columns belong
    to each MFA group. All features with missing values and 0 variance (if
    filter_zero_variance = True) are dropped. If a group is empty after filtering it
    is also dropped and the user is warned.

    Args:
        tables (dict | None): Feature table groups where keys are MFA group
            names and values are DataFrames.
        sample_metadata (Metadata | None): Optional sample metadata to include
            as MFA groups.
        metadata_groups (str | dict | None): Optional metadata group specification.
        filter_zero_variance (bool): Whether to remove zero-variance columns
            before ordination.

    Returns:
        tuple[pd.DataFrame, dict]: A tuple containing:
            - pd.DataFrame: MFA input table with prefixed feature columns.
            - dict: MFA group names mapped to column names.
    """
    tables = {} if tables is None else dict(getattr(tables, "collection", tables))

    metadata_tables = _metadata_to_grouped_tables(sample_metadata, metadata_groups)

    duplicate_groups = sorted(set(tables).intersection(metadata_tables))
    if duplicate_groups:
        raise ValueError(
            "Metadata group names cannot duplicate feature table group names: "
            f"{', '.join(duplicate_groups)}"
        )
    tables.update(metadata_tables)

    for group_name in tables:
        _validate_group_name(group_name)

    table_values = list(tables.values())
    consensus_samples = (
        reduce(
            lambda shared, table: shared.intersection(table.index),
            table_values[1:],
            table_values[0].index,
        )
        if table_values
        else pd.Index([])
    )

    if table_values and consensus_samples.empty:
        raise ValueError("MFA inputs do not share any sample IDs.")

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
        table = drop_columns_with_missing_values(table)
        if filter_zero_variance:
            table = drop_zero_variance_columns(table)
        if table.empty:
            warnings.warn(
                (
                    f"\033[33mDropped MFA group '{group_name}' because all "
                    "features were removed during missing value filtering or "
                    "zero-variance filtering.\033[0m"
                ),
                UserWarning,
                stacklevel=2,
            )
            continue
        prefixed_tables.append(table)
        groups[group_name] = list(table.columns)

    if len(groups) < 2:
        raise ValueError(
            "MFA requires at least two groups after filtering. Groups may have "
            "been removed because all features were removed during missing "
            "value filtering or zero-variance filtering."
        )

    return pd.concat(prefixed_tables, axis=1), groups


def mfa(
    tables: pd.DataFrame = None,
    sample_metadata: Metadata = None,
    metadata_groups: dict = None,
    rescale_with_mean: bool = True,
    rescale_with_std: bool = True,
    n_components: int = 2,
    n_iter: int = 3,
    random_state: CaptureHolder[int] = None,
    engine: str = "sklearn",
    filter_zero_variance: bool = True,
) -> ComponentAnalysisDirFmt:
    """
    Runs Multiple Factor Analysis and writes all Prince-derived outputs.

    Combines feature tables and optional sample metadata into Prince's MFA input
    representation, fits ``prince.MFA``, and serializes the ordination plus
    MFA-specific coordinate, contribution, correlation, and cosine-similarity
    tables into a component-analysis directory format.

    Args:
        tables (pd.DataFrame | None): Feature table collection where each
            collection key is treated as an MFA group.
        sample_metadata (Metadata | None): Optional sample metadata to include
            as MFA groups.
        metadata_groups (dict | None): Optional metadata group mapping where
            keys are group names and values are comma-separated metadata column
            names.
        rescale_with_mean (bool): Whether Prince should center features before
            SVD.
        rescale_with_std (bool): Whether Prince should standardize features
            before SVD.
        n_components (int): Number of principal components to compute.
        n_iter (int): Number of iterations used by the randomized SVD engine.
        random_state (CaptureHolder[int] | None): Random seed capture used for
            reproducible randomized SVD.
        engine (str): Prince SVD engine to use.
        filter_zero_variance (bool): Whether to remove zero-variance columns
            before ordination.

    Returns:
        ComponentAnalysisDirFmt: Component-analysis directory format containing
            the MFA ordination and numeric Prince output tables.
    """
    random_state = resolve_random_state(random_state, engine)

    mfa_params = locals()
    mfa_params.pop("tables")
    mfa_params.pop("sample_metadata")
    mfa_params.pop("metadata_groups")
    mfa_params.pop("filter_zero_variance")

    table, groups = _build_prince_input(
        tables,
        sample_metadata,
        metadata_groups,
        filter_zero_variance=filter_zero_variance,
    )

    mfa_result = prince.MFA(**mfa_params).fit(table, groups=groups)

    ordination = OrdinationResults(
        short_method_name="MFA",
        long_method_name="Multiple Factor Analysis",
        eigvals=pd.Series(mfa_result.eigenvalues_),
        samples=mfa_result.row_coordinates(table),
        features=mfa_result.column_coordinates_,
        proportion_explained=pd.Series(mfa_result.percentage_of_variance_),
    )
    results = ComponentAnalysisDirFmt()
    results.ordination.write_data(ordination, OrdinationResults)
    numeric_outputs = {
        results.partial_sample_coordinates: mfa_result.partial_row_coordinates(table),
        results.sample_cosine_similarities: mfa_result.row_cosine_similarities(table),
        results.sample_contributions: mfa_result.row_contributions_,
        results.group_coordinates: mfa_result.group_coordinates_,
        results.group_contributions: mfa_result.group_contributions_,
        results.group_cosine_similarities: mfa_result.group_cosine_similarities_,
        results.partial_correlations: mfa_result.partial_correlations_,
        results.partial_contributions: mfa_result.partial_contributions_,
        results.feature_correlations: mfa_result.column_correlations,
        results.feature_contributions: mfa_result.column_contributions_,
        results.feature_cosine_similarities: mfa_result.column_cosine_similarities_,
    }
    for output, data in numeric_outputs.items():
        output.write_data(data, pd.DataFrame)

    return results
