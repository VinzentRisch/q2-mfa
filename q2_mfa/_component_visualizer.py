# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import json
from contextlib import ExitStack
from importlib import resources
from pathlib import Path
from shutil import copyfile

import numpy as np
import pandas as pd
import q2templates
from rachis import Metadata

from q2_mfa.types import ComponentAnalysisDirFmt

_TEMPLATE_FILES = ("index.html",)
_STATIC_ASSET_FILES = (
    "style.css",
    "app.js",
    "plotly-basic-2.35.2.min.js",
    "plotly-basic-2.35.2.min.js.LICENSE.txt",
)
# Stored precision for the numeric value arrays. The plot is pixel-identical and
# every displayed value is trimmed well below this, so 6 decimals roughly halves
# the embedded payload with no visible change.
_PAYLOAD_FLOAT_DECIMALS = 6
_SHARED_REQUIRED_TABLES = (
    "eigenvalues",
    "percentage_of_variance",
    "cumulative_percentage_of_variance",
    "sample_coordinates",
    "sample_contributions",
    "sample_cosine_similarities",
    "feature_coordinates",
    "feature_correlations",
    "feature_contributions",
    "feature_cosine_similarities",
)
_MFA_REQUIRED_TABLES = (
    "group_coordinates",
    "group_contributions",
    "group_cosine_similarities",
    "partial_sample_coordinates",
    "partial_correlations",
)


def component_visualizer(
    output_dir: str,
    component_analysis: ComponentAnalysisDirFmt,
    analysis_type: str,
    sample_metadata: Metadata = None,
):
    """
    Writes an interactive PCA or MFA visualization from component-analysis tables.

    Args:
        output_dir (str): The directory where visualization assets are written.
        component_analysis (ComponentAnalysisDirFmt): The JSONL-backed
            component-analysis result directory format.
        analysis_type (str): Whether to render the result as PCA or MFA.
        sample_metadata (Metadata | None): Optional sample metadata used for
            browser-side coloring, sizing, and filtering.

    Returns:
        None
    """
    payload = _build_payload(component_analysis, analysis_type, sample_metadata)
    _write_visualization(output_dir, payload)


def _build_payload(
    component_analysis: ComponentAnalysisDirFmt,
    analysis_type: str,
    sample_metadata: Metadata = None,
) -> dict[str, object]:
    """
    Builds the browser payload from long JSONL result tables.

    Args:
        component_analysis (ComponentAnalysisDirFmt): The JSONL-backed
            component-analysis result directory format.
        analysis_type (str): Whether to render the result as PCA or MFA.
        sample_metadata (Metadata | None): Optional sample metadata to attach
            by sample ID.

    Returns:
        dict[str, object]: The JSON-serializable visualization payload.
    """
    table_names = _SHARED_REQUIRED_TABLES
    if analysis_type == "mfa":
        table_names = (*table_names, *_MFA_REQUIRED_TABLES)
    tables = {
        table_name: getattr(component_analysis, table_name).view(pd.DataFrame)
        for table_name in table_names
    }
    dimensions = _build_dimensions(
        tables["eigenvalues"],
        tables["percentage_of_variance"],
        tables["cumulative_percentage_of_variance"],
    )
    sample_ids = list(
        dict.fromkeys(
            str(sample_id) for sample_id in tables["sample_coordinates"]["sample_id"]
        )
    )
    if sample_metadata is None:
        metadata = pd.DataFrame(index=sample_ids)
    else:
        metadata = sample_metadata.to_dataframe().copy()
        metadata.index = metadata.index.astype(str)
        metadata = metadata.reindex(sample_ids)

    metadata_columns, metadata_types = _build_metadata_columns(metadata)
    samples = _build_samples(
        tables["sample_coordinates"],
        tables["sample_contributions"],
        tables["sample_cosine_similarities"],
        metadata,
        metadata_columns,
        metadata_types,
    )
    features = _build_features(
        tables["feature_coordinates"],
        tables["feature_correlations"],
        tables["feature_contributions"],
        tables["feature_cosine_similarities"],
        analysis_type,
    )
    groups = []
    partial_samples = []
    partial_axes = []
    if analysis_type == "mfa":
        groups = _build_groups(
            tables["group_coordinates"],
            tables["group_contributions"],
            tables["group_cosine_similarities"],
        )
        partial_samples = _build_component_entities(
            tables["partial_sample_coordinates"],
            ("sample_id", "group"),
            component_column="partial_component",
            value_columns={"coordinate": "value"},
        )
        partial_axes = _build_component_entities(
            tables["partial_correlations"],
            ("group", "partial_component"),
            component_column="component",
            value_columns={"correlation": "value"},
        )
    return {
        "analysis_type": analysis_type,
        "default_x": dimensions[0]["component"],
        "default_y": dimensions[1]["component"],
        "dimensions": dimensions,
        "metadata_columns": metadata_columns,
        "samples": samples,
        "features": features,
        "groups": groups,
        "partial_samples": partial_samples,
        "partial_axes": partial_axes,
    }


def _build_dimensions(
    eigenvalues: pd.DataFrame,
    percentage_of_variance: pd.DataFrame,
    cumulative_percentage_of_variance: pd.DataFrame,
) -> list[dict[str, object]]:
    """
    Builds component metadata from variance JSONL records.

    Args:
        eigenvalues (pd.DataFrame): Long eigenvalue table.
        percentage_of_variance (pd.DataFrame): Long percentage-variance table.
        cumulative_percentage_of_variance (pd.DataFrame): Long cumulative
            percentage-variance table.

    Returns:
        list[dict[str, object]]: Component metadata ordered by component ID.
    """
    dimensions = []
    for _, row in percentage_of_variance.sort_values("component").iterrows():
        component = int(row["component"])
        explained = float(row["value"])
        label = f"Dim {component + 1}"
        dimensions.append(
            {
                "component": component,
                "label": label,
                "axis_title": f"{label} ({explained:.1f}% explained)",
                "eigenvalue": float(eigenvalues.loc[component, "value"]),
                "variance_explained": explained,
                "cumulative_variance_explained": float(
                    cumulative_percentage_of_variance.loc[component, "value"]
                ),
            }
        )

    return dimensions


def _build_samples(
    sample_coordinates: pd.DataFrame,
    sample_contributions: pd.DataFrame,
    sample_cosine_similarities: pd.DataFrame,
    metadata: pd.DataFrame,
    metadata_columns: list[dict[str, object]],
    metadata_types: dict[str, str],
) -> list[dict[str, object]]:
    """
    Builds sample view-model records for browser-side plotting and controls.

    Args:
        sample_coordinates (pd.DataFrame): Long sample coordinate records.
        sample_contributions (pd.DataFrame): Long sample contribution records.
        sample_cosine_similarities (pd.DataFrame): Long sample cos2 records.
        metadata (pd.DataFrame): Metadata rows reindexed to sample coordinates,
            or an empty-column frame indexed by sample ID when metadata is not
            provided.
        metadata_columns (list[dict[str, object]]): Included metadata columns.
        metadata_types (dict[str, str]): Metadata column type lookup.

    Returns:
        list[dict[str, object]]: Sample records with metadata and component
            values.
    """
    included_columns = [column["name"] for column in metadata_columns]
    merged = _merge_value_tables(
        {
            "coordinate": sample_coordinates,
            "contribution": sample_contributions,
            "cos2": sample_cosine_similarities,
        },
        ["sample_id", "component"],
    )
    arrays_by_sample = _component_arrays_by_entity(
        merged,
        ("sample_id",),
        component_column="component",
        value_columns={
            "coordinate": "coordinate",
            "contribution": "contribution",
            "cos2": "cos2",
        },
    )
    samples = []
    sample_ids = list(
        dict.fromkeys(str(sample_id) for sample_id in sample_coordinates["sample_id"])
    )
    for sample_id in sample_ids:
        row = metadata.loc[sample_id]
        metadata_row = {}
        for column_name in included_columns:
            metadata_row[column_name] = _to_json_value(
                row[column_name], metadata_types[column_name]
            )
        sample = {"sample_id": str(sample_id), "metadata": metadata_row}
        sample.update(arrays_by_sample[(str(sample_id),)])
        samples.append(sample)
    return samples


def _build_features(
    feature_coordinates: pd.DataFrame,
    feature_correlations: pd.DataFrame,
    feature_contributions: pd.DataFrame,
    feature_cosine_similarities: pd.DataFrame,
    analysis_type: str,
) -> list[dict[str, object]]:
    """
    Builds feature view-model records with coordinate and correlation values.

    Args:
        feature_coordinates (pd.DataFrame): Long feature coordinate records.
        feature_correlations (pd.DataFrame): Long feature correlation records.
        feature_contributions (pd.DataFrame): Long feature contribution
            records.
        feature_cosine_similarities (pd.DataFrame): Long feature cos2 records.
        analysis_type (str): The plugin-constrained analysis type slug.

    Returns:
        list[dict[str, object]]: Feature records keyed by variable and, for MFA,
            group.
    """
    key_columns = ("group", "variable") if analysis_type == "mfa" else ("variable",)
    join_columns = [*key_columns, "component"]
    merged = _merge_value_tables(
        {
            "coordinate": feature_coordinates,
            "correlation": feature_correlations,
            "contribution": feature_contributions,
            "cos2": feature_cosine_similarities,
        },
        join_columns,
    )
    return _build_component_entities(
        merged,
        key_columns,
        component_column="component",
        value_columns={
            "coordinate": "coordinate",
            "correlation": "correlation",
            "contribution": "contribution",
            "cos2": "cos2",
        },
    )


def _build_groups(
    group_coordinates: pd.DataFrame,
    group_contributions: pd.DataFrame,
    group_cosine_similarities: pd.DataFrame,
) -> list[dict[str, object]]:
    """
    Builds group view-model records with per-component summary values.

    Args:
        group_coordinates (pd.DataFrame): Long group coordinate records.
        group_contributions (pd.DataFrame): Long group contribution records.
        group_cosine_similarities (pd.DataFrame): Long group cos2 records.

    Returns:
        list[dict[str, object]]: Group records with component summaries.
    """
    merged = _merge_value_tables(
        {
            "coordinate": group_coordinates,
            "contribution": group_contributions,
            "cos2": group_cosine_similarities,
        },
        ["group", "component"],
    )

    return _build_component_entities(
        merged,
        ("group",),
        component_column="component",
        value_columns={
            "coordinate": "coordinate",
            "contribution": "contribution",
            "cos2": "cos2",
        },
    )


def _merge_value_tables(
    tables: dict[str, pd.DataFrame], join_columns: list[str]
) -> pd.DataFrame:
    """
    Merges same-shaped long value tables on shared key columns.

    Args:
        tables (dict[str, pd.DataFrame]): Mapping of output value names to
            source tables containing a generic value column.
        join_columns (list[str]): Columns used to join the tables.

    Returns:
        pd.DataFrame: Merged table with semantic value columns.
    """
    merged = None
    for value_name, table in tables.items():
        renamed = table.rename(columns={"value": value_name})
        if merged is None:
            merged = renamed
            continue
        merged = merged.merge(renamed, on=join_columns, how="outer")
    return merged


def _build_component_entities(
    table: pd.DataFrame,
    key_columns: tuple[str, ...],
    component_column: str,
    value_columns: dict[str, str],
) -> list[dict[str, object]]:
    """
    Builds entity records with grouped component values.

    Args:
        table (pd.DataFrame): The long component table.
        key_columns (tuple[str, ...]): Columns to copy onto each entity.
        component_column (str): The source component column.
        value_columns (dict[str, str]): Mapping of output component field names
            to input table column names.

    Returns:
        list[dict[str, object]]: Entity records with columnar value arrays.
    """
    arrays_by_entity = _component_arrays_by_entity(
        table,
        key_columns,
        component_column=component_column,
        value_columns=value_columns,
    )
    entities = []
    for key, arrays in arrays_by_entity.items():
        entity = dict(zip(key_columns, key))
        entity.update(arrays)
        entities.append(entity)
    return entities


def _component_arrays_by_entity(
    table: pd.DataFrame,
    key_columns: tuple[str, ...],
    component_column: str,
    value_columns: dict[str, str],
) -> dict[tuple, dict[str, list]]:
    """
    Groups long component rows into per-entity columnar value arrays.

    Each entity maps to a dict of output field name -> list indexed by component
    id (list position). This columnar layout lets the browser read a value with
    an O(1) index (``entity[field][component]``) and keeps the embedded payload
    small by writing each field name once per entity instead of once per
    component. Missing components are filled with ``None``.

    Args:
        table (pd.DataFrame): The long component table.
        key_columns (tuple[str, ...]): Columns that identify each entity.
        component_column (str): The source component column.
        value_columns (dict[str, str]): Mapping of output field names to input
            table column names.

    Returns:
        dict[tuple, dict[str, list]]: Per-entity columnar value arrays.
    """
    keys = list(key_columns)
    n_components = int(table[component_column].max()) + 1

    ordered_keys = table[keys].drop_duplicates()
    entity_index = (
        pd.Index(ordered_keys[keys[0]])
        if len(keys) == 1
        else pd.MultiIndex.from_frame(ordered_keys)
    )

    # Reshape each long value column to a dense (entity x component) matrix in a
    # single vectorized pass.
    field_rows = {}
    for output_name, source_column in value_columns.items():
        wide = table.pivot_table(
            index=keys,
            columns=component_column,
            values=source_column,
            aggfunc="first",
        ).reindex(index=entity_index, columns=range(n_components))

        matrix = np.round(wide.to_numpy(dtype=float), _PAYLOAD_FLOAT_DECIMALS)
        rows = matrix.tolist()
        if np.isnan(matrix).any():
            rows = [
                [None if value != value else value for value in row] for row in rows
            ]
        field_rows[output_name] = rows

    grouped = {}
    for position, key in enumerate(entity_index):
        key_tuple = (
            (_to_python_json_value(key),)
            if len(keys) == 1
            else tuple(_to_python_json_value(value) for value in key)
        )
        grouped[key_tuple] = {
            output_name: field_rows[output_name][position]
            for output_name in value_columns
        }
    return grouped


def _build_metadata_columns(
    metadata: pd.DataFrame,
) -> tuple[list[dict[str, object]], dict[str, str]]:
    """
    Builds metadata control descriptors and type lookup.

    Args:
        metadata (pd.DataFrame): Sample metadata reindexed to plotted samples.

    Returns:
        tuple[list[dict[str, object]], dict[str, str]]: Metadata column
            descriptors and their inferred types.
    """
    columns = []
    column_types = {}

    for column_name in metadata.columns:
        series = metadata[column_name]
        if series.dropna().empty:
            continue

        if pd.api.types.is_numeric_dtype(series):
            column_types[column_name] = "numeric"
            columns.append(
                {
                    "name": column_name,
                    "type": "numeric",
                    "min": float(series.min(skipna=True)),
                    "max": float(series.max(skipna=True)),
                    "has_missing": bool(series.isna().any()),
                }
            )
            continue

        column_types[column_name] = "categorical"
        columns.append(
            {
                "name": column_name,
                "type": "categorical",
                "values": sorted({str(value) for value in series.dropna()}),
                "has_missing": bool(series.isna().any()),
            }
        )

    return columns, column_types


def _to_json_value(value, column_type: str):
    """
    Converts one metadata value to a JSON-compatible scalar.

    Args:
        value: The metadata value.
        column_type (str): The inferred metadata column type.

    Returns:
        object: A JSON-compatible scalar or None.
    """
    if pd.isna(value):
        return None

    if column_type == "numeric":
        return float(value)

    return str(value)


def _to_python_json_value(value):
    """
    Converts pandas and NumPy scalar values to JSON-compatible Python values.

    Args:
        value: The value to normalize.

    Returns:
        object: A JSON-compatible scalar or None.
    """
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _write_visualization(output_dir: str, payload: dict[str, object]):
    """
    Writes rendered visualization assets and the embedded data payload.

    Args:
        output_dir (str): The output directory.
        payload (dict[str, object]): The JSON-serializable payload.

    Returns:
        None
    """
    output_path = Path(output_dir)
    asset_dir = resources.files("q2_mfa") / "assets" / "component_visualizer"

    with ExitStack() as stack:
        template_paths = [
            str(stack.enter_context(resources.as_file(asset_dir / template_name)))
            for template_name in _TEMPLATE_FILES
        ]
        q2templates.render(
            template_paths,
            output_dir,
            context={},
        )

    for asset_name in _STATIC_ASSET_FILES:
        with resources.as_file(asset_dir / asset_name) as source_path:
            copyfile(source_path, output_path / asset_name)

    data_path = output_path / "data.js"
    data_path.write_text(
        f"window.COMPONENT_VISUALIZER_DATA = {json.dumps(payload)};\n",
        encoding="utf-8",
    )
