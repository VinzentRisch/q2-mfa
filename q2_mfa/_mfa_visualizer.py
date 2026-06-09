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

from q2_mfa.types import ComponentAnalysisDirFmt

_TEMPLATE_FILES = ("index.html",)
_STATIC_ASSET_FILES = (
    "style.css",
    "app.js",
    "plotly-basic-2.35.2.min.js",
    "plotly-basic-2.35.2.min.js.LICENSE.txt",
)


def mfa_visualizer(
    output_dir: str, mfa_results: ComponentAnalysisDirFmt, sample_metadata: Metadata
):
    (
        ordination,
        partial_sample_coordinates,
        group_summary,
        partial_correlations,
        feature_correlations,
    ) = _load_mfa_visualizer_inputs(mfa_results)

    payload = _build_payload(
        ordination,
        sample_metadata,
        partial_sample_coordinates,
        group_summary,
        partial_correlations,
        feature_correlations,
    )
    _write_visualization(output_dir, payload)


def _load_mfa_visualizer_inputs(
    mfa_results: ComponentAnalysisDirFmt,
) -> tuple[
    OrdinationResults,
    pd.DataFrame,
    dict[str, pd.DataFrame],
    pd.DataFrame,
    pd.DataFrame,
]:
    ordination = OrdinationResults.read(str(mfa_results.path / "ordination.txt"))
    partial_sample_coordinates = _read_prince_wide_tsv(
        mfa_results.path / "partial-sample-coordinates.tsv"
    )
    group_summary = {
        "coordinates": _read_prince_wide_tsv(
            mfa_results.path / "group-coordinates.tsv"
        ),
        "contributions": _read_prince_wide_tsv(
            mfa_results.path / "group-contributions.tsv"
        ),
        "cos2": _read_prince_wide_tsv(
            mfa_results.path / "group-cosine-similarities.tsv"
        ),
    }
    partial_correlations = _read_prince_wide_tsv(
        mfa_results.path / "partial-correlations.tsv"
    )
    feature_correlations = pd.read_csv(
        mfa_results.path / "feature-correlations.tsv", sep="\t"
    )
    return (
        ordination,
        partial_sample_coordinates,
        group_summary,
        partial_correlations,
        feature_correlations,
    )


def _build_payload(
    ordination: OrdinationResults,
    sample_metadata: Metadata,
    partial_sample_coordinates: pd.DataFrame,
    group_summary: dict[str, pd.DataFrame],
    partial_correlations: pd.DataFrame,
    feature_correlations: pd.DataFrame,
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
    partial_samples, partial_groups = _build_partial_sample_payload(
        partial_sample_coordinates,
        sample_coordinates.index,
        dimensions,
    )
    group_summary_payload = _build_group_summary_payload(group_summary, dimensions)
    partial_correlations_payload = _build_partial_correlation_payload(
        partial_correlations, dimensions
    )
    feature_coordinate_payload = _build_feature_coordinate_payload(
        ordination.features, dimensions
    )
    feature_correlation_payload = _build_feature_correlation_payload(
        feature_correlations, dimensions
    )

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
        "partial_groups": partial_groups,
        "partial_samples": partial_samples,
        "group_summary": group_summary_payload,
        "partial_correlations": partial_correlations_payload,
        "feature_coordinates": feature_coordinate_payload,
        "feature_correlations": feature_correlation_payload,
    }


def _build_partial_sample_payload(
    partial_sample_coordinates: pd.DataFrame,
    sample_ids: pd.Index,
    dimensions: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[str]]:
    dim_lookup = _build_zero_indexed_dimension_lookup(dimensions)
    grouped = {}
    groups = set()
    for _, row in partial_sample_coordinates.iterrows():
        sample_id = str(row["id"])
        for column_name, value in row.items():
            if column_name == "id":
                continue
            group, dimension = _split_group_dimension_column(column_name)
            groups.add(group)
            grouped.setdefault((sample_id, group), {})[dim_lookup[dimension]] = float(
                value
            )

    partial_samples = []
    ordered_groups = sorted(groups)
    for sample_id in sample_ids:
        for group in ordered_groups:
            partial_samples.append(
                {
                    "sample_id": sample_id,
                    "group": group,
                    "coords": grouped[(sample_id, group)],
                }
            )

    return partial_samples, ordered_groups


def _build_group_summary_payload(
    group_summary: dict[str, pd.DataFrame],
    dimensions: list[dict[str, object]],
) -> list[dict[str, object]]:
    coordinate_table = group_summary["coordinates"]
    contribution_table = group_summary["contributions"]
    cos2_table = group_summary["cos2"]

    contribution_by_group = _index_by_id(contribution_table)
    cos2_by_group = _index_by_id(cos2_table)
    dim_lookup = _build_zero_indexed_dimension_lookup(dimensions)
    payload = []
    for _, coordinate_row in coordinate_table.iterrows():
        group = str(coordinate_row["id"])
        contribution_row = contribution_by_group[group]
        cos2_row = cos2_by_group[group]

        group_entry = {
            "group": group,
            "coords": {},
            "contribution": {},
            "cos2": {},
        }
        for dimension, dim_key in dim_lookup.items():
            column_name = str(dimension)
            group_entry["coords"][dim_key] = float(coordinate_row[column_name])
            group_entry["contribution"][dim_key] = float(contribution_row[column_name])
            group_entry["cos2"][dim_key] = float(cos2_row[column_name])

        payload.append(group_entry)

    return sorted(payload, key=lambda entry: entry["group"])


def _build_partial_correlation_payload(
    partial_correlations: pd.DataFrame,
    dimensions: list[dict[str, object]],
) -> list[dict[str, object]]:
    dim_lookup = _build_zero_indexed_dimension_lookup(dimensions)
    payload = []
    for _, row in partial_correlations.iterrows():
        group, partial_axis = _split_group_dimension_column(row["id"])
        for dimension, dim_key in dim_lookup.items():
            column_name = str(dimension)
            payload.append(
                {
                    "group": group,
                    "partial_axis": partial_axis + 1,
                    "global_dim": dim_key,
                    "value": float(row[column_name]),
                }
            )

    return payload


def _build_feature_correlation_payload(
    feature_correlations: pd.DataFrame,
    dimensions: list[dict[str, object]],
) -> list[dict[str, object]]:
    dimension_columns = _build_zero_indexed_dimension_lookup(dimensions)

    payload = []
    for _, row in feature_correlations.iterrows():
        feature_id = str(row["id"])
        group, feature_name = feature_id.split(":", 1)
        coords = {}
        for column in dimension_columns:
            column = str(column)
            value = row[column]
            coords[dimension_columns[int(column)]] = (
                None if pd.isna(value) else float(value)
            )

        payload.append(
            {
                "feature_id": feature_id,
                "group": group,
                "feature_name": feature_name,
                "coords": coords,
            }
        )

    return payload


def _build_feature_coordinate_payload(
    feature_coordinates: pd.DataFrame,
    dimensions: list[dict[str, object]],
) -> list[dict[str, object]]:
    dimension_columns = {
        str(dimension["source_key"]): dimension["key"] for dimension in dimensions
    }

    payload = []
    feature_coordinates = feature_coordinates.copy()
    feature_coordinates.index = feature_coordinates.index.astype(str)
    feature_coordinates.columns = feature_coordinates.columns.astype(str)
    for feature_id, row in feature_coordinates.iterrows():
        group, feature_name = _split_feature_id(feature_id)
        coords = {}
        for column_name, dimension_key in dimension_columns.items():
            value = row[column_name]
            coords[dimension_key] = None if pd.isna(value) else float(value)

        payload.append(
            {
                "feature_id": feature_id,
                "group": group,
                "feature_name": feature_name,
                "coords": coords,
            }
        )

    return payload


def _split_feature_id(feature_id: str) -> tuple[str, str]:
    if ":" not in feature_id:
        return "Ungrouped", feature_id

    return feature_id.split(":", 1)


def _read_prince_wide_tsv(path: Path) -> pd.DataFrame:
    table = pd.read_csv(path, sep="\t")
    table["id"] = table["id"].astype(str)
    return table


def _build_zero_indexed_dimension_lookup(
    dimensions: list[dict[str, object]],
) -> dict[int, str]:
    return {index: dimension["key"] for index, dimension in enumerate(dimensions)}


def _split_group_dimension_column(column_name: str) -> tuple[str, int]:
    group, dimension = str(column_name).split(":", 1)
    return group, int(dimension)


def _index_by_id(table: pd.DataFrame) -> dict[str, pd.Series]:
    return {str(row["id"]): row for _, row in table.iterrows()}


def _build_dimensions(
    sample_coordinates: pd.DataFrame, proportion_explained: pd.Series
) -> list[dict[str, object]]:
    dimensions = []
    for index, column_name in enumerate(sample_coordinates.columns):
        explained = float(proportion_explained.iloc[index])
        label = f"Dim {index + 1}"
        axis_title = f"{label} ({explained:.1f}% explained)"

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
            context={},
        )

    for asset_name in _STATIC_ASSET_FILES:
        with resources.as_file(asset_dir / asset_name) as source_path:
            copyfile(source_path, output_path / asset_name)

    data_path = output_path / "data.js"
    data_path.write_text(
        f"window.MFA_VISUALIZER_DATA = {json.dumps(payload)};\n",
        encoding="utf-8",
    )
