# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import shutil
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from q2_types.tabular import TableJSONLFileFormat
from q2_types.tabular._deferred_setup._transformers import (
    df_to_table_jsonl,
    table_jsonl_to_df,
)
from skbio import OrdinationResults

from q2_mfa.plugin_setup import plugin

from ._format import ComponentAnalysisDirFmt
from ._result import ComponentAnalysis


@dataclass(frozen=True)
class _TableSpec:
    attr: str
    kind: str
    index: str | None = None
    required: bool = True


_TABLE_SPECS = (
    _TableSpec("eigenvalues", "series"),
    _TableSpec("percentage_of_variance", "series"),
    _TableSpec("cumulative_percentage_of_variance", "series"),
    _TableSpec("sample_coordinates", "wide", index="sample_id"),
    _TableSpec("sample_cosine_similarities", "wide", index="sample_id"),
    _TableSpec("sample_contributions", "wide", index="sample_id"),
    _TableSpec("feature_coordinates", "wide", index="variable"),
    _TableSpec("feature_correlations", "wide", index="variable"),
    _TableSpec("feature_contributions", "wide", index="variable"),
    _TableSpec("feature_cosine_similarities", "wide", index="variable"),
    _TableSpec("group_coordinates", "wide", index="group", required=False),
    _TableSpec("group_contributions", "wide", index="group", required=False),
    _TableSpec("group_cosine_similarities", "wide", index="group", required=False),
    _TableSpec("partial_sample_coordinates", "multi_columns", required=False),
    _TableSpec("partial_correlations", "multi_rows", required=False),
    _TableSpec("partial_contributions", "multi_rows", required=False),
)


@plugin.register_transformer
def _component_analysis_to_dirfmt(
    result: ComponentAnalysis,
) -> ComponentAnalysisDirFmt:
    """
    Converts a ComponentAnalysis result to a ComponentAnalysisDirFmt.

    Args:
        result (ComponentAnalysis): The PCA or MFA result object.

    Returns:
        ComponentAnalysisDirFmt: The JSONL-backed directory format.
    """
    ff = ComponentAnalysisDirFmt()
    for spec in _TABLE_SPECS:
        table = getattr(result, spec.attr)
        if table is None:
            if spec.required:
                raise ValueError(f"Missing required table: {spec.attr}.")
            continue
        _write_result_table(ff.path / f"{spec.attr}.jsonl", table, spec)
    return ff


@plugin.register_transformer
def _dirfmt_to_component_analysis(
    ff: ComponentAnalysisDirFmt,
) -> ComponentAnalysis:
    """
    Converts ComponentAnalysisDirFmt to a ComponentAnalysis object.

    Args:
        ff (ComponentAnalysisDirFmt): The JSONL-backed directory format.

    Returns:
        ComponentAnalysis: The reconstructed result.
    """
    kwargs = {}
    for spec in _TABLE_SPECS:
        path = ff.path / f"{spec.attr}.jsonl"
        if not path.exists():
            kwargs[spec.attr] = None
            continue
        kwargs[spec.attr] = _read_result_table(path, spec)
    return ComponentAnalysis(**kwargs)


@plugin.register_transformer
def _dirfmt_to_ordination_results(
    ff: ComponentAnalysisDirFmt,
) -> OrdinationResults:
    """
    Converts ComponentAnalysisDirFmt to scikit-bio ordination results.

    Args:
        ff (ComponentAnalysisDirFmt): The JSONL-backed directory format.

    Returns:
        OrdinationResults: The reconstructed ordination result.
    """
    result = _dirfmt_to_component_analysis(ff)
    method = "MFA" if result.is_mfa else "PCA"
    long_name = (
        "Multiple Factor Analysis" if result.is_mfa else "Principal Component Analysis"
    )
    return OrdinationResults(
        short_method_name=method,
        long_method_name=long_name,
        eigvals=result.eigenvalues,
        samples=result.sample_coordinates,
        features=result.feature_coordinates,
        proportion_explained=result.percentage_of_variance / 100,
    )


def _write_result_table(
    path: Path, table: pd.DataFrame | pd.Series, spec: _TableSpec
) -> None:
    """
    Writes a result table in long TableJSONL form.

    Args:
        path (Path): The JSONL output path.
        table (pd.DataFrame | pd.Series): The table or series to write.
        spec (_TableSpec): The table serialization specification.

    Returns:
        None
    """
    if spec.kind == "series":
        records = _series_to_long(table)
    elif spec.kind == "wide":
        records = _wide_to_long(table, spec.index)
    elif spec.kind == "multi_columns":
        records = _multi_columns_to_long(table)
    elif spec.kind == "multi_rows":
        records = _multi_rows_to_long(table)
    else:  # pragma: no cover
        raise ValueError(f"Unknown table kind: {spec.kind}.")
    jsonl = df_to_table_jsonl(records.reset_index(drop=True).convert_dtypes())
    shutil.copyfile(str(jsonl), path)


def _read_result_table(path: Path, spec: _TableSpec) -> pd.DataFrame | pd.Series:
    """
    Reads a long TableJSONL result table into Prince-shaped wide form.

    Args:
        path (Path): The JSONL input path.
        spec (_TableSpec): The table serialization specification.

    Returns:
        pd.DataFrame | pd.Series: The reconstructed wide table or series.
    """
    table = table_jsonl_to_df(TableJSONLFileFormat(str(path), mode="r"))
    if spec.kind == "series":
        return _read_series(table)
    elif spec.kind == "wide":
        return _long_to_wide(table, spec)
    elif spec.kind == "multi_columns":
        return _long_to_multi_columns(table)
    elif spec.kind == "multi_rows":
        return _long_to_multi_rows(table)
    else:  # pragma: no cover
        raise ValueError(f"Unknown table kind: {spec.kind}.")


def _wide_to_long(table: pd.DataFrame, index: str) -> pd.DataFrame:
    """
    Converts a simple wide table to long component records.

    Args:
        table (pd.DataFrame): The wide table.
        index (str): The storage column name for the row index.

    Returns:
        pd.DataFrame: Long records for JSONL storage.
    """
    working = table.copy()
    working.index.name = index
    return working.reset_index().melt(
        id_vars=[index], var_name="component", value_name="value"
    )


def _long_to_wide(table: pd.DataFrame, spec: _TableSpec) -> pd.DataFrame:
    """
    Reconstructs a simple wide table from long component records.

    Args:
        table (pd.DataFrame): The long table records.
        spec (_TableSpec): The table serialization specification.

    Returns:
        pd.DataFrame: The reconstructed wide table.
    """
    index = spec.index
    wide_table = table.pivot(index=index, columns="component", values="value")
    wide_table.index.name = None if index == "sample_id" else index
    wide_table.columns.name = "component"
    wide_table.index = _restore_identifier_index(wide_table.index)
    wide_table.columns = _restore_identifier_index(wide_table.columns)
    return wide_table


def _multi_columns_to_long(table: pd.DataFrame) -> pd.DataFrame:
    """
    Converts partial sample coordinates with MultiIndex columns to long records.

    Args:
        table (pd.DataFrame): The partial sample coordinate table.

    Returns:
        pd.DataFrame: Long records for JSONL storage.
    """
    records = table.stack(level=[0, 1], future_stack=True).reset_index()
    records.columns = ["sample_id", "group", "partial_component", "value"]
    return records


def _long_to_multi_columns(table: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstructs partial sample coordinates with MultiIndex columns.

    Args:
        table (pd.DataFrame): The long table records.
    Returns:
        pd.DataFrame: The reconstructed partial sample coordinate table.
    """
    partial_table = table.pivot(
        index="sample_id", columns=["group", "partial_component"], values="value"
    )
    partial_table.index.name = None
    partial_table.columns.names = [None, None]
    partial_table.index = _restore_identifier_index(partial_table.index)
    partial_table.columns = _restore_identifier_index(partial_table.columns)
    return partial_table


def _multi_rows_to_long(table: pd.DataFrame) -> pd.DataFrame:
    """
    Converts partial-axis tables with MultiIndex rows to long records.

    Args:
        table (pd.DataFrame): A partial correlation or contribution table.

    Returns:
        pd.DataFrame: Long records for JSONL storage.
    """
    working = table.copy()
    working.index = working.index.set_names(["group", "partial_component"])
    return working.reset_index().melt(
        id_vars=["group", "partial_component"],
        var_name="component",
        value_name="value",
    )


def _long_to_multi_rows(table: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstructs a partial-axis table with MultiIndex rows.

    Args:
        table (pd.DataFrame): The long table records.
    Returns:
        pd.DataFrame: The reconstructed partial-axis table.
    """
    partial_table = table.pivot(
        index=["group", "partial_component"], columns="component", values="value"
    )
    partial_table.index = partial_table.index.set_names(["group", "component"])
    partial_table.columns.name = "component"
    partial_table.index = _restore_identifier_index(partial_table.index)
    partial_table.columns = _restore_identifier_index(partial_table.columns)
    return partial_table


def _restore_identifier_index(index: pd.Index) -> pd.Index:
    """
    Restores string identifier levels to object dtype.

    TableJSONL reads string columns as pandas string-extension dtype, while
    Prince returns sample, feature, and group identifiers as object string
    labels. Numeric component labels are preserved.

    Args:
        index (pd.Index): The index or MultiIndex to normalize.

    Returns:
        pd.Index: The index with string identifier levels restored to object
            dtype.
    """
    if isinstance(index, pd.MultiIndex):
        levels = [
            level.astype(object) if pd.api.types.is_string_dtype(level) else level
            for level in index.levels
        ]
        return index.set_levels(levels)
    if pd.api.types.is_string_dtype(index):
        return index.astype(object)
    return index


def _series_to_long(series: pd.Series) -> pd.DataFrame:
    """
    Converts a component-indexed Series to long records.

    Args:
        series (pd.Series): The component-indexed values to write.

    Returns:
        pd.DataFrame: Long records for JSONL storage.
    """
    working = series.copy()
    records = working.rename("value").reset_index()
    records.columns = ["component", "value"]
    return records


def _read_series(table: pd.DataFrame) -> pd.Series:
    """
    Reconstructs a component-indexed Series from long table records.

    Args:
        table (pd.DataFrame): The long table records read from TableJSONL,
            with ``component`` and ``value`` columns.

    Returns:
        pd.Series: The reconstructed component-indexed values.
    """
    series = table.set_index("component")["value"].astype(float)
    series.index.name = "component"
    series.name = None
    return series
