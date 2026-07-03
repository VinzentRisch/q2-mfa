# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import json
from collections.abc import Mapping
from contextlib import ExitStack
from importlib import resources
from pathlib import Path
from shutil import copyfile

import numpy as np
import pandas as pd
import q2templates
from rachis import Metadata

from q2_mfa.types import ComponentAnalysis

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


def component_visualizer(
    output_dir: str,
    component_analysis: ComponentAnalysis,
    analysis_type: str,
    sample_metadata: Metadata = None,
):
    """
    Writes an interactive PCA or MFA visualization from component-analysis tables.

    Args:
        output_dir (str): The directory where visualization assets are written.
        component_analysis (ComponentAnalysis): The reconstructed component-analysis
            result object holding Prince-shaped wide tables.
        analysis_type (str): Whether to render the result as PCA or MFA.
        sample_metadata (Metadata | None): Optional sample metadata used for
            browser-side coloring, sizing, and filtering.

    Returns:
        None
    """
    payload = _build_payload(component_analysis, analysis_type, sample_metadata)
    _write_visualization(output_dir, payload)


def _build_payload(
    component_analysis: ComponentAnalysis,
    analysis_type: str,
    sample_metadata: Metadata = None,
) -> dict[str, object]:
    """
    Builds the browser payload from the Prince-shaped wide result tables.

    Args:
        component_analysis (ComponentAnalysis): The reconstructed
            component-analysis result object holding wide tables and vectors.
        analysis_type (str): Whether to render the result as PCA or MFA.
        sample_metadata (Metadata | None): Optional sample metadata to attach
            by sample ID.

    Returns:
        dict[str, object]: The JSON-serializable visualization payload.
    """
    # Build Dimensions
    dimensions = _build_dimensions(
        component_analysis.eigenvalues,
        component_analysis.percentage_of_variance,
        component_analysis.cumulative_percentage_of_variance,
    )

    # Build Metadata
    sample_ids = [
        str(sample_id) for sample_id in component_analysis.sample_coordinates.index
    ]
    if sample_metadata is None:
        metadata = pd.DataFrame(index=sample_ids)
    else:
        metadata = sample_metadata.to_dataframe().copy()
        metadata.index = metadata.index.astype(str)
        metadata = metadata.reindex(sample_ids)

    metadata_columns, metadata_types = _build_metadata_columns(metadata)

    # Build Samples
    samples = _build_samples(
        component_analysis.sample_coordinates,
        component_analysis.sample_contributions,
        component_analysis.sample_cosine_similarities,
        metadata,
        metadata_columns,
        metadata_types,
    )

    # Build Features
    # PCA feature tables have a flat ``variable`` index; MFA tables have a
    # ``(group, variable)`` MultiIndex.
    feature_key_columns = (
        ("group", "variable") if analysis_type == "mfa" else ("variable",)
    )
    features = _build_component_entities(
        {
            "coordinate": component_analysis.feature_coordinates,
            "correlation": component_analysis.feature_correlations,
            "contribution": component_analysis.feature_contributions,
            "cos2": component_analysis.feature_cosine_similarities,
        },
        feature_key_columns,
    )
    groups = []
    partial_samples = []
    partial_axes = []
    if analysis_type == "mfa":
        # Build Groups
        groups = _build_component_entities(
            {
                "coordinate": component_analysis.group_coordinates,
                "contribution": component_analysis.group_contributions,
                "cos2": component_analysis.group_cosine_similarities,
            },
            ("group",),
        )

        # Build Partial sample Coordinates
        # Move the group column level onto the row index so each partial sample
        # record is keyed by (sample_id, group), leaving partial components as
        # the columns.
        stacked = component_analysis.partial_sample_coordinates.stack(
            level=0, future_stack=True
        )
        stacked.index = stacked.index.set_names(["sample_id", "group"])
        partial_samples = _build_component_entities(
            {"coordinate": stacked},
            ("sample_id", "group"),
        )

        # Build Partial Axes
        partial_axes = _build_component_entities(
            {
                "correlation": component_analysis.partial_correlations,
                "contribution": component_analysis.partial_contributions,
            },
            ("group", "partial_component"),
        )
    return {
        "analysis_type": analysis_type,
        "dimensions": dimensions,
        "metadata_columns": metadata_columns,
        "samples": samples,
        "features": features,
        "groups": groups,
        "partial_samples": partial_samples,
        "partial_axes": partial_axes,
    }


def _build_dimensions(
    eigenvalues: np.ndarray,
    percentage_of_variance: np.ndarray,
    cumulative_percentage_of_variance: np.ndarray,
) -> list[dict[str, object]]:
    """
    Builds component metadata from the variance vectors.

    Args:
        eigenvalues (np.ndarray): Eigenvalue per component.
        percentage_of_variance (np.ndarray): Percentage of variance per component.
        cumulative_percentage_of_variance (np.ndarray): Cumulative percentage of
            variance per component.

    Returns:
        list[dict[str, object]]: Component metadata ordered by component ID.
    """
    dimensions = []
    for component in range(len(percentage_of_variance)):
        explained = float(percentage_of_variance[component])
        label = f"Dim {component + 1}"
        dimensions.append(
            {
                "component": component,
                "label": label,
                "axis_title": f"{label} ({explained:.1f}% explained)",
                "eigenvalue": float(eigenvalues[component]),
                "variance_explained": explained,
                "cumulative_variance_explained": float(
                    cumulative_percentage_of_variance[component]
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
        sample_coordinates (pd.DataFrame): Wide sample coordinate table
            (index = sample ID, columns = components).
        sample_contributions (pd.DataFrame): Wide sample contribution table.
        sample_cosine_similarities (pd.DataFrame): Wide sample cos2 table.
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
    records = _build_component_entities(
        {
            "coordinate": sample_coordinates,
            "contribution": sample_contributions,
            "cos2": sample_cosine_similarities,
        },
        ("sample_id",),
    )
    samples = []
    for record in records:
        sample_id = str(record["sample_id"])
        row = metadata.loc[sample_id]
        metadata_row = {}
        for column_name in included_columns:
            metadata_row[column_name] = _to_json_value(
                row[column_name], metadata_types[column_name]
            )
        sample = {"sample_id": sample_id, "metadata": metadata_row}
        for field in ("coordinate", "contribution", "cos2"):
            sample[field] = record[field]
        samples.append(sample)
    return samples


def _build_component_entities(
    fields: Mapping[str, pd.DataFrame | None],
    key_columns: tuple[str, ...],
) -> list[dict[str, object]]:
    """
    Builds entity records with columnar per-component value arrays from wide
    tables.

    Each field is a wide ``entity x component`` table sharing the same row index.
    Secondary fields are aligned to the first field's index order, then each row
    becomes a list indexed by component id (list position). This columnar layout
    lets the browser read a value with an O(1) index (``entity[field][component]``)
    and keeps the embedded payload small by writing each field name once per
    entity. Missing components are filled with ``None``.

    Tables are typed optional because the MFA-only result tables are ``None`` on a
    PCA result, but every field passed here is expected to be present; a ``None``
    is treated as a caller error.

    Args:
        fields (Mapping[str, pd.DataFrame | None]): Mapping of output field names
            to wide source tables. The first entry defines the entity order.
        key_columns (tuple[str, ...]): Names for the entity identifier levels,
            paired positionally with the (possibly Multi-) index values.

    Returns:
        list[dict[str, object]]: Entity records with columnar value arrays.
    """
    primary = next(iter(fields.values()))
    if primary is None:
        raise ValueError("The first component field must be a table, not None.")
    index = primary.index
    key_tuples = _index_key_tuples(index)
    field_rows = {}
    for name, table in fields.items():
        if table is None:
            raise ValueError(f"Missing component table for field '{name}'.")
        field_rows[name] = _wide_value_rows(table.reindex(index))
    entities = []
    for position, key_tuple in enumerate(key_tuples):
        entity = dict(zip(key_columns, key_tuple))
        for name in fields:
            entity[name] = field_rows[name][position]
        entities.append(entity)
    return entities


def _wide_value_rows(wide: pd.DataFrame) -> list[list]:
    """
    Converts a wide ``entity x component`` table to per-entity value rows.

    Components are densified to a contiguous ``0..max`` range, values are rounded
    to the stored precision, and NaNs (missing components/entities) become
    ``None``.

    Args:
        wide (pd.DataFrame): The wide table (columns are component ids).

    Returns:
        list[list]: One list of per-component values per row, in index order.
    """
    n_components = int(max(wide.columns)) + 1 if len(wide.columns) else 0
    matrix = np.round(
        wide.reindex(columns=range(n_components)).to_numpy(dtype=float),
        _PAYLOAD_FLOAT_DECIMALS,
    )
    rows = matrix.tolist()
    if np.isnan(matrix).any():
        rows = [[None if value != value else value for value in row] for row in rows]
    return rows


def _index_key_tuples(index: pd.Index) -> list[tuple]:
    """
    Normalizes a (possibly Multi-) index into JSON-compatible key tuples.

    Args:
        index (pd.Index): The entity row index.

    Returns:
        list[tuple]: One key tuple per index entry.
    """
    if isinstance(index, pd.MultiIndex):
        return [tuple(_to_python_json_value(value) for value in key) for key in index]
    return [(_to_python_json_value(key),) for key in index]


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
