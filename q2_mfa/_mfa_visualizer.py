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

import pandas as pd
import q2templates
from rachis import Metadata
from skbio import OrdinationResults

_TEMPLATE_FILES = ("index.html", "graphs.html")
_STATIC_ASSET_FILES = ("style.css", "app.js")


def mfa_visualizer(
    output_dir: str, mfa_results: OrdinationResults, sample_metadata: Metadata
):
    sample_coordinates = mfa_results.samples
    if sample_coordinates is None or sample_coordinates.empty:
        raise ValueError("MFA results must contain sample coordinates.")

    if sample_coordinates.shape[1] < 2:
        raise ValueError("MFA visualization requires at least two sample dimensions.")

    payload = _build_payload(mfa_results, sample_metadata)
    _write_visualization(output_dir, payload)


def _build_payload(
    ordination: OrdinationResults, sample_metadata: Metadata
) -> dict[str, object]:
    sample_coordinates = ordination.samples.copy()
    sample_coordinates.index = sample_coordinates.index.astype(str)
    sample_coordinates.columns = sample_coordinates.columns.astype(str)

    metadata = sample_metadata.to_dataframe().copy()
    metadata.index = metadata.index.astype(str)
    metadata = metadata.reindex(sample_coordinates.index)

    dimensions = _build_dimensions(sample_coordinates, ordination.proportion_explained)
    dimension_keys = {
        dimension["source_key"]: dimension["key"] for dimension in dimensions
    }
    metadata_columns, metadata_types = _build_metadata_columns(metadata)

    included_columns = [column["name"] for column in metadata_columns]
    samples = []
    for sample_id, coordinates in sample_coordinates.iterrows():
        metadata_row = {}
        for column_name in included_columns:
            value = metadata.at[sample_id, column_name]
            metadata_row[column_name] = _to_json_value(
                value, metadata_types[column_name]
            )

        samples.append(
            {
                "sample_id": sample_id,
                "coords": {
                    dimension_keys[column_name]: float(value)
                    for column_name, value in coordinates.items()
                },
                "metadata": metadata_row,
            }
        )

    return {
        "title": "MFA sample scores",
        "tabs": [{"url": "graphs.html", "title": "Graphs"}],
        "default_tab": "graphs",
        "default_x": dimensions[0]["key"],
        "default_y": dimensions[1]["key"],
        "dimensions": dimensions,
        "component_variance": [
            {
                "key": dimension["key"],
                "label": dimension["label"],
                "variance_explained": dimension["variance_explained"],
            }
            for dimension in dimensions
        ],
        "metadata_columns": metadata_columns,
        "samples": samples,
    }


def _build_dimensions(
    sample_coordinates: pd.DataFrame, proportion_explained: pd.Series | None
) -> list[dict[str, object]]:
    dimensions = []
    for index, column_name in enumerate(sample_coordinates.columns):
        explained = None
        if proportion_explained is not None and index < len(proportion_explained):
            explained_value = proportion_explained.iloc[index]
            if pd.notna(explained_value):
                explained = float(explained_value)

        label = f"Dim {index + 1}"
        axis_title = label
        if explained is not None:
            axis_title = f"{label} ({explained * 100:.1f}% explained)"

        dimensions.append(
            {
                "key": label,
                "label": label,
                "source_key": column_name,
                "axis_title": axis_title,
                "variance_explained": explained,
            }
        )

    return dimensions


def _build_metadata_columns(
    metadata: pd.DataFrame,
) -> tuple[list[dict[str, object]], dict[str, str]]:
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
    if pd.isna(value):
        return None

    if column_type == "numeric":
        return float(value)

    return str(value)


def _write_visualization(output_dir: str, payload: dict[str, object]):
    output_path = Path(output_dir)
    asset_dir = resources.files("q2_mfa") / "assets" / "mfa_visualizer"

    with ExitStack() as stack:
        template_paths = [
            str(stack.enter_context(resources.as_file(asset_dir / template_name)))
            for template_name in _TEMPLATE_FILES
        ]
        q2templates.render(
            template_paths,
            output_dir,
            context={"tabs": payload["tabs"]},
        )

    for asset_name in _STATIC_ASSET_FILES:
        with resources.as_file(asset_dir / asset_name) as source_path:
            copyfile(source_path, output_path / asset_name)

    data_path = output_path / "data.js"
    data_path.write_text(
        f"window.MFA_VISUALIZER_DATA = {json.dumps(payload)};\n",
        encoding="utf-8",
    )
