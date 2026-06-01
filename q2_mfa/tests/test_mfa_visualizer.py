# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import json
import tempfile
from pathlib import Path

from rachis import Metadata
from rachis.plugin.testing import TestPluginBase

from q2_mfa._mfa_visualizer import mfa_visualizer
from q2_mfa.types import MFAResultsDirFmt


class TestMFAVisualizer(TestPluginBase):
    package = "q2_mfa.tests"

    @classmethod
    def setUpClass(cls):
        instance = cls()
        cls.metadata = Metadata.load(
            instance.get_data_path("mfa_vis/sample_metadata.tsv")
        )
        cls.mfa_results = MFAResultsDirFmt(
            instance.get_data_path("mfa/mfa_vis_results"),
            mode="r",
        )

    def _load_payload(self, output_dir):
        prefix = "window.MFA_VISUALIZER_DATA = "
        data = Path(output_dir) / "data.js"
        payload = data.read_text(encoding="utf-8")
        self.assertTrue(payload.startswith(prefix))
        return json.loads(payload[len(prefix) :].rstrip(";\n"))

    def test_plugin_registers_mfa_visualizer(self):
        self.assertIn("mfa_visualizer", self.plugin.visualizers)

    def test_mfa_visualizer_writes_expected_assets_and_payload(self):
        with tempfile.TemporaryDirectory() as output_dir:
            mfa_visualizer(output_dir, self.mfa_results, self.metadata)

            for filename in (
                "index.html",
                "style.css",
                "app.js",
                "plotly-basic-2.35.2.min.js",
                "plotly-basic-2.35.2.min.js.LICENSE.txt",
                "data.js",
            ):
                self.assertTrue((Path(output_dir) / filename).exists())

            index_html = (Path(output_dir) / "index.html").read_text(encoding="utf-8")
            self.assertIn(
                '<script src="plotly-basic-2.35.2.min.js"></script>',
                index_html,
            )
            self.assertIn('id="top-features-table-body"', index_html)
            self.assertIn('id="download-feature-table"', index_html)
            self.assertIn(
                '<label for="top-feature-count">Number of loadings</label>',
                index_html,
            )
            self.assertIn(
                '<input id="top-feature-count" type="number" min="1" '
                'max="100" step="1" value="10">',
                index_html,
            )
            self.assertIn('class="plot-shell plot-shell-main"', index_html)
            for expected_tooltip_text in (
                "visible sample scores from ordination.txt",
                "partial coordinates from partial-sample-coordinates.tsv",
                "global sample scores from ordination.txt",
                "feature correlations from feature-correlations.tsv",
                "sqrt(x^2 + y^2)",
                "proportion explained values stored in ordination.txt",
                "running total calculated from the component proportion "
                "explained values in ordination.txt",
                "group coordinates from group-coordinates.tsv",
                "contribution values from group-contributions.tsv",
                "cos2 values from group-cosine-similarities.tsv",
                "partial axis correlations from partial-correlations.tsv",
                "Ranks all features from feature-correlations.tsv",
            ):
                self.assertIn(expected_tooltip_text, index_html)
            for sort_key in (
                "rank",
                "feature_name",
                "group",
                "x",
                "y",
                "rankingScore",
            ):
                self.assertIn(f'data-feature-sort="{sort_key}"', index_html)
            self.assertNotIn("https://cdn.plot.ly", index_html)

            style_css = (Path(output_dir) / "style.css").read_text(encoding="utf-8")
            self.assertIn("max-height: min(70vh, 780px);", style_css)
            self.assertIn("table-layout: fixed;", style_css)
            self.assertIn(".feature-table-number {\n  text-align: left;", style_css)
            self.assertIn("justify-content: flex-start;", style_css)
            self.assertIn("color-scheme: light;", style_css)
            self.assertIn("font-family: Arial, sans-serif;", style_css)
            self.assertNotIn("IBM Plex", style_css)
            self.assertNotIn("Helvetica Neue", style_css)
            self.assertIn("font-size: 0.9rem;", style_css)
            self.assertIn("font-size: 0.92rem;", style_css)
            self.assertIn("font-size: 0.95rem;", style_css)
            self.assertIn(
                ".feature-table-download {\n  appearance: none;\n"
                "  border: 1px solid var(--control-border);\n"
                "  border-radius: 8px;\n"
                "  background: var(--control-bg);\n"
                "  color: var(--text-muted);",
                style_css,
            )
            self.assertIn(
                ".filter-placeholder {\n  color: var(--text-main);\n"
                "  font-size: 0.9rem;",
                style_css,
            )
            self.assertIn("resize: horizontal;", style_css)
            self.assertIn("max-width: 100%;", style_css)
            self.assertIn("container-type: inline-size;", style_css)
            self.assertIn("height: calc(100cqw - 34px);", style_css)
            self.assertNotIn(".plot-shell-main::after", style_css)
            self.assertNotIn("height: 640px;", style_css)

            app_js = (Path(output_dir) / "app.js").read_text(encoding="utf-8")
            self.assertIn("function bindSamplePlotResizeObserver()", app_js)
            self.assertIn("new ResizeObserver", app_js)
            self.assertIn("Plotly.Plots.resize('sample-plot')", app_js)
            self.assertIn("family: 'Arial, sans-serif'", app_js)
            self.assertNotIn("IBM Plex", app_js)
            self.assertNotIn("Helvetica Neue", app_js)
            self.assertIn("function formatSampleLegendName(name, samples)", app_js)
            self.assertIn("return `${name} (${samples.length})`;", app_js)
            self.assertIn("name: formatSampleLegendName(name, samples),", app_js)
            self.assertIn(
                "name: formatSampleLegendName(colorColumn.name, numericSamples),",
                app_js,
            )
            self.assertIn(
                "const SECONDARY_SQUARE_PLOT_MARGIN = { t: 20, r: 46, b: 70, l: 80 };",
                app_js,
            )
            self.assertIn(
                "const VARIANCE_PLOT_MARGIN = { t: 20, r: 20, b: 42, l: 80 };",
                app_js,
            )
            self.assertIn(
                "const CUMULATIVE_VARIANCE_PLOT_MARGIN = "
                "{ t: 28, r: 56, b: 42, l: 80 };",
                app_js,
            )
            self.assertEqual(app_js.count("margin: SECONDARY_SQUARE_PLOT_MARGIN"), 2)
            self.assertIn("margin: VARIANCE_PLOT_MARGIN,", app_js)
            self.assertIn("margin: CUMULATIVE_VARIANCE_PLOT_MARGIN,", app_js)
            self.assertIn("const PARTIAL_AXES_Y_RANGE = [-1.19, 1.19];", app_js)
            self.assertEqual(app_js.count("scaleanchor: 'y',"), 2)
            self.assertGreaterEqual(app_js.count("constrain: 'domain',"), 4)
            self.assertNotIn("zeroline: false,", app_js)
            self.assertNotIn("zerolinewidth: 2,", app_js)
            self.assertIn("function computeSampleLegendRightMargin(traces)", app_js)
            self.assertIn(
                "const legendRightMargin = computeSampleLegendRightMargin(traces);",
                app_js,
            )
            self.assertIn(
                "margin: { t: 32, r: legendRightMargin, b: 70, l: 80 },", app_js
            )
            self.assertIn("SAMPLE_LEGEND_MAX_RIGHT_MARGIN = 420;", app_js)
            self.assertIn("function updateSamplePlotResizeLimits(layout)", app_js)
            self.assertIn("updateSamplePlotResizeLimits(layout);", app_js)
            self.assertIn(
                "samplePlotShell.style.minWidth = `min(${minimumShellWidth}px, 100%)`;",
                app_js,
            )
            self.assertIn("text: dimensionsByKey[state.xDimension].label,", app_js)
            self.assertIn("text: dimensionsByKey[state.yDimension].label,", app_js)
            self.assertNotIn(
                "text: `${dimensionsByKey[state.xDimension].label} partial inertia`,",
                app_js,
            )
            self.assertNotIn(
                "text: `${dimensionsByKey[state.yDimension].label} partial inertia`,",
                app_js,
            )
            self.assertIn("orientation: 'v',", app_js)
            self.assertIn("x: 1.02,", app_js)
            self.assertIn("const MAX_FEATURE_OVERLAY_COUNT = 100;", app_js)
            self.assertIn("topFeatureCount: 10,", app_js)
            self.assertIn("hoverinfo: 'skip'", app_js)
            self.assertNotIn(
                "customdata: labelPlacement.map((label) => label.hoverText)",
                app_js,
            )
            self.assertIn(
                "const groupLegend = `feature-correlations:${group}`;",
                app_js,
            )
            self.assertIn(
                "const groupLabelPlacement = labelPlacement.filter("
                "(label) => label.group === group);",
                app_js,
            )
            self.assertIn("group: feature.group,", app_js)
            self.assertIn("group: item.group,", app_js)
            self.assertIn(
                "buildPlotLabelConnectorTraces(groupLabelPlacement, {\n"
                "      legendgroup: groupLegend,",
                app_js,
            )
            self.assertIn(
                "buildPlotLabelTrace(groupLabelPlacement, 11, {\n"
                "      legendgroup: groupLegend,",
                app_js,
            )
            self.assertIn("function getSortedFeatureTableRows()", app_js)
            self.assertIn("function updateFeatureTableSort(button)", app_js)
            self.assertIn("function downloadFeatureTableTsv()", app_js)
            self.assertIn("function escapeTsvValue(value)", app_js)
            self.assertIn("const features = getSortedFeatureTableRows();", app_js)

            payload = self._load_payload(output_dir)

        self.assertEqual(payload["default_x"], "Dim 1")
        self.assertEqual(payload["default_y"], "Dim 2")
        self.assertEqual(
            [dimension["label"] for dimension in payload["dimensions"]],
            ["Dim 1", "Dim 2"],
        )
        self.assertEqual(
            [dimension["axis_title"] for dimension in payload["dimensions"]],
            ["Dim 1 (0.8% explained)", "Dim 2 (0.2% explained)"],
        )
        self.assertEqual(
            payload["component_variance"],
            [
                {
                    "key": "Dim 1",
                    "label": "Dim 1",
                    "variance_explained": 0.8,
                },
                {
                    "key": "Dim 2",
                    "label": "Dim 2",
                    "variance_explained": 0.2,
                },
            ],
        )

        metadata_columns = {
            column["name"]: column for column in payload["metadata_columns"]
        }
        self.assertEqual(metadata_columns["body_site"]["type"], "categorical")
        self.assertEqual(metadata_columns["body_site"]["values"], ["gut", "skin"])
        self.assertEqual(metadata_columns["age"]["type"], "numeric")
        self.assertEqual(metadata_columns["age"]["min"], 23.0)
        self.assertEqual(metadata_columns["age"]["max"], 35.0)

        sample_ids = [sample["sample_id"] for sample in payload["samples"]]
        self.assertEqual(sample_ids, ["sample-1", "sample-2", "sample-3"])
        self.assertEqual(payload["samples"][0]["coords"], {"Dim 1": 1.0, "Dim 2": 0.1})
        self.assertEqual(
            payload["samples"][0]["metadata"],
            {
                "body_site": "gut",
                "cohort": "control",
                "age": 23.0,
                "bmi": 20.5,
            },
        )

    def test_mfa_visualizer_parses_prince_mfa_results(self):
        with tempfile.TemporaryDirectory() as output_dir:
            mfa_visualizer(output_dir, self.mfa_results, self.metadata)
            payload = self._load_payload(output_dir)

        self.assertEqual(payload["partial_groups"], ["A", "B"])
        self.assertNotIn("partial_axes", payload)
        self.assertEqual(
            {payload["default_x"], payload["default_y"]},
            {"Dim 1", "Dim 2"},
        )
        for sample in payload["samples"]:
            self.assertEqual(set(sample["coords"]), {"Dim 1", "Dim 2"})
        for partial_sample in payload["partial_samples"]:
            self.assertEqual(set(partial_sample["coords"]), {"Dim 1", "Dim 2"})
        for group in payload["group_summary"]:
            self.assertEqual(set(group["coords"]), {"Dim 1", "Dim 2"})
            self.assertEqual(set(group["contribution"]), {"Dim 1", "Dim 2"})
            self.assertEqual(set(group["cos2"]), {"Dim 1", "Dim 2"})
        self.assertEqual(
            {
                (entry["partial_axis"], entry["global_dim"])
                for entry in payload["partial_correlations"]
            },
            {
                (1, "Dim 1"),
                (1, "Dim 2"),
                (2, "Dim 1"),
                (2, "Dim 2"),
            },
        )
        for feature in payload["feature_correlations"]:
            self.assertEqual(set(feature["coords"]), {"Dim 1", "Dim 2"})
        self.assertEqual(
            [component["key"] for component in payload["component_variance"]],
            ["Dim 1", "Dim 2"],
        )

        self.assertEqual(
            payload["partial_samples"],
            [
                {
                    "sample_id": "sample-1",
                    "group": "A",
                    "coords": {"Dim 1": 0.9, "Dim 2": 0.11},
                },
                {
                    "sample_id": "sample-1",
                    "group": "B",
                    "coords": {"Dim 1": 1.1, "Dim 2": 0.09},
                },
                {
                    "sample_id": "sample-2",
                    "group": "A",
                    "coords": {"Dim 1": 1.8, "Dim 2": 0.21},
                },
                {
                    "sample_id": "sample-2",
                    "group": "B",
                    "coords": {"Dim 1": 2.2, "Dim 2": 0.19},
                },
                {
                    "sample_id": "sample-3",
                    "group": "A",
                    "coords": {"Dim 1": 2.7, "Dim 2": 0.31},
                },
                {
                    "sample_id": "sample-3",
                    "group": "B",
                    "coords": {"Dim 1": 3.3, "Dim 2": 0.29},
                },
            ],
        )

        self.assertEqual(
            payload["group_summary"],
            [
                {
                    "group": "A",
                    "coords": {"Dim 1": 0.42, "Dim 2": 0.12},
                    "contribution": {"Dim 1": 0.35, "Dim 2": 0.45},
                    "cos2": {"Dim 1": 0.72, "Dim 2": 0.18},
                },
                {
                    "group": "B",
                    "coords": {"Dim 1": 0.58, "Dim 2": 0.28},
                    "contribution": {"Dim 1": 0.65, "Dim 2": 0.55},
                    "cos2": {"Dim 1": 0.83, "Dim 2": 0.27},
                },
            ],
        )
        for group in payload["group_summary"]:
            self.assertNotIn("first_eigenvalue", group)
            self.assertNotIn("weight", group)

        self.assertEqual(
            payload["partial_correlations"],
            [
                {
                    "group": "A",
                    "partial_axis": 1,
                    "global_dim": "Dim 1",
                    "value": 0.88,
                },
                {
                    "group": "A",
                    "partial_axis": 1,
                    "global_dim": "Dim 2",
                    "value": 0.12,
                },
                {
                    "group": "A",
                    "partial_axis": 2,
                    "global_dim": "Dim 1",
                    "value": 0.05,
                },
                {
                    "group": "A",
                    "partial_axis": 2,
                    "global_dim": "Dim 2",
                    "value": 0.74,
                },
                {
                    "group": "B",
                    "partial_axis": 1,
                    "global_dim": "Dim 1",
                    "value": 0.67,
                },
                {
                    "group": "B",
                    "partial_axis": 1,
                    "global_dim": "Dim 2",
                    "value": 0.22,
                },
                {
                    "group": "B",
                    "partial_axis": 2,
                    "global_dim": "Dim 1",
                    "value": 0.11,
                },
                {
                    "group": "B",
                    "partial_axis": 2,
                    "global_dim": "Dim 2",
                    "value": 0.82,
                },
            ],
        )

        self.assertEqual(
            payload["feature_correlations"],
            [
                {
                    "feature_id": "A:feature-a",
                    "group": "A",
                    "feature_name": "feature-a",
                    "coords": {"Dim 1": 0.71, "Dim 2": -0.21},
                },
                {
                    "feature_id": "B:taxon:b:variant",
                    "group": "B",
                    "feature_name": "taxon:b:variant",
                    "coords": {"Dim 1": 0.62, "Dim 2": 0.44},
                },
            ],
        )
