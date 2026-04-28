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

from q2_mfa.types import MFAResultsDirFmt

_TEMPLATE_FILES = ("index.html",)
_STATIC_ASSET_FILES = ("style.css", "app.js")


def mfa_visualizer(
    output_dir: str, mfa_results: MFAResultsDirFmt, sample_metadata: Metadata
):
    (
        ordination,
        partial_sample_coordinates,
        group_summary,
        partial_axes,
        feature_correlations,
    ) = _load_mfa_visualizer_inputs(mfa_results)
    sample_coordinates = ordination.samples
    if sample_coordinates is None or sample_coordinates.empty:
        raise ValueError("MFA results must contain sample coordinates.")

    if sample_coordinates.shape[1] < 2:
        raise ValueError("MFA visualization requires at least two sample dimensions.")

    payload = _build_payload(
        ordination,
        sample_metadata,
        partial_sample_coordinates,
        group_summary,
        partial_axes,
        feature_correlations,
    )
    _write_visualization(output_dir, payload)


def _load_mfa_visualizer_inputs(
    mfa_results,
) -> tuple[
    OrdinationResults,
    pd.DataFrame | None,
    pd.DataFrame | None,
    pd.DataFrame | None,
    pd.DataFrame | None,
]:
    if isinstance(mfa_results, OrdinationResults):
        return mfa_results, None, None, None, None

    if isinstance(mfa_results, MFAResultsDirFmt):
        ordination = OrdinationResults.read(str(mfa_results.path / "ordination.txt"))
        partial_scores = pd.read_csv(mfa_results.path / "partial-scores.tsv", sep="\t")
        group_summary = pd.read_csv(mfa_results.path / "group-summary.tsv", sep="\t")
        partial_axes = pd.read_csv(mfa_results.path / "partial-axes.tsv", sep="\t")
        feature_correlations = pd.read_csv(
            mfa_results.path / "feature-correlations.tsv", sep="\t"
        )
        return (
            ordination,
            partial_scores,
            group_summary,
            partial_axes,
            feature_correlations,
        )

    if hasattr(mfa_results, "path"):
        path = Path(mfa_results.path)
        ordination_path = path / "ordination.txt"
        partial_scores_path = path / "partial-scores.tsv"
        if ordination_path.exists():
            ordination = OrdinationResults.read(str(ordination_path))
            partial_scores = None
            if partial_scores_path.exists():
                partial_scores = pd.read_csv(partial_scores_path, sep="\t")
            group_summary = None
            group_summary_path = path / "group-summary.tsv"
            if group_summary_path.exists():
                group_summary = pd.read_csv(group_summary_path, sep="\t")
            partial_axes = None
            partial_axes_path = path / "partial-axes.tsv"
            if partial_axes_path.exists():
                partial_axes = pd.read_csv(partial_axes_path, sep="\t")
            feature_correlations = None
            feature_correlations_path = path / "feature-correlations.tsv"
            if feature_correlations_path.exists():
                feature_correlations = pd.read_csv(feature_correlations_path, sep="\t")
            return (
                ordination,
                partial_scores,
                group_summary,
                partial_axes,
                feature_correlations,
            )

    raise TypeError(
        "mfa_results must be an OrdinationResults object or an MFAResults directory "
        "view."
    )


def _build_payload(
    ordination: OrdinationResults,
    sample_metadata: Metadata,
    partial_sample_coordinates: pd.DataFrame | None = None,
    group_summary: pd.DataFrame | None = None,
    partial_axes: pd.DataFrame | None = None,
    feature_correlations: pd.DataFrame | None = None,
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
    partial_axes_payload = _build_partial_axes_payload(partial_axes, dimensions)
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
        "partial_axes": partial_axes_payload,
        "feature_correlations": feature_correlation_payload,
    }


def _build_partial_sample_payload(
    partial_sample_coordinates: pd.DataFrame | None,
    sample_ids: pd.Index,
    dimensions: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[str]]:
    if partial_sample_coordinates is None or partial_sample_coordinates.empty:
        return [], []

    partial_scores = partial_sample_coordinates.copy()
    partial_scores["sample_id"] = partial_scores["sample_id"].astype(str)
    partial_scores["group"] = partial_scores["group"].astype(str)

    dim_lookup = {
        index + 1: dimension["key"] for index, dimension in enumerate(dimensions)
    }
    partial_scores = partial_scores[partial_scores["dim"].isin(dim_lookup)]
    if partial_scores.empty:
        return [], []

    partial_scores["dimension_key"] = partial_scores["dim"].map(dim_lookup)
    grouped = {}
    for row in partial_scores.itertuples(index=False):
        grouped.setdefault((row.sample_id, row.group), {})[row.dimension_key] = float(
            row.coordinate
        )

    partial_samples = []
    for sample_id in sample_ids:
        for group in sorted(partial_scores["group"].unique()):
            coords = grouped.get((sample_id, group))
            if coords is None:
                continue
            partial_samples.append(
                {
                    "sample_id": sample_id,
                    "group": group,
                    "coords": coords,
                }
            )

    return partial_samples, sorted(partial_scores["group"].unique())


def _build_group_summary_payload(
    group_summary: pd.DataFrame | None,
    dimensions: list[dict[str, object]],
) -> list[dict[str, object]]:
    if group_summary is None or group_summary.empty:
        return []

    dim_lookup = {
        index + 1: dimension["key"] for index, dimension in enumerate(dimensions)
    }
    summary = group_summary.copy()
    summary["group"] = summary["group"].astype(str)
    summary = summary[summary["dim"].isin(dim_lookup)]
    if summary.empty:
        return []

    grouped = {}
    for row in summary.itertuples(index=False):
        group_entry = grouped.setdefault(
            row.group,
            {
                "group": row.group,
                "coords": {},
                "contribution": {},
                "cos2": {},
                "first_eigenvalue": float(row.first_eigenvalue),
                "weight": float(row.weight),
            },
        )
        dim_key = dim_lookup[row.dim]
        group_entry["coords"][dim_key] = float(row.coordinate)
        group_entry["contribution"][dim_key] = float(row.contribution)
        group_entry["cos2"][dim_key] = float(row.cos2)

    return [grouped[group] for group in sorted(grouped)]


def _build_partial_axes_payload(
    partial_axes: pd.DataFrame | None,
    dimensions: list[dict[str, object]],
) -> list[dict[str, object]]:
    if partial_axes is None or partial_axes.empty:
        return []

    dim_lookup = {
        index + 1: dimension["key"] for index, dimension in enumerate(dimensions)
    }
    axes = partial_axes.copy()
    axes["group"] = axes["group"].astype(str)
    axes = axes[axes["global_dim"].isin(dim_lookup)]
    if axes.empty:
        return []

    return [
        {
            "group": str(row.group),
            "partial_axis": int(row.partial_axis),
            "global_dim": dim_lookup[row.global_dim],
            "value": float(row.value),
        }
        for row in axes.itertuples(index=False)
    ]


def _build_feature_correlation_payload(
    feature_correlations: pd.DataFrame | None,
    dimensions: list[dict[str, object]],
) -> list[dict[str, object]]:
    if feature_correlations is None or feature_correlations.empty:
        return []

    correlation_table = feature_correlations.copy()
    dimension_columns = {
        str(index + 1): dimension["key"] for index, dimension in enumerate(dimensions)
    }
    available_dimension_columns = [
        column for column in dimension_columns if column in correlation_table.columns
    ]
    if not available_dimension_columns:
        return []

    correlation_table["feature_id"] = correlation_table["feature_id"].astype(str)
    correlation_table["group"] = correlation_table["group"].astype(str)
    correlation_table["feature_name"] = correlation_table["feature_name"].astype(str)

    payload = []
    for _, row in correlation_table.iterrows():
        coords = {}
        for column in available_dimension_columns:
            value = row[column]
            coords[dimension_columns[column]] = None if pd.isna(value) else float(value)

        payload.append(
            {
                "feature_id": row["feature_id"],
                "group": row["group"],
                "feature_name": row["feature_name"],
                "coords": coords,
            }
        )

    return payload


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
