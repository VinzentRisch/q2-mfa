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

from q2_mfa._component_visualizer import component_visualizer
from q2_mfa.types import ComponentAnalysisDirFmt
from q2_mfa.types._transformer import _dirfmt_to_component_analysis


class TestComponentVisualizer(TestPluginBase):
    package = "q2_mfa.tests"

    @classmethod
    def setUpClass(cls):
        instance = cls()
        cls.metadata = Metadata.load(instance.get_data_path("mfa/mfa_vis_metadata.tsv"))
        # The visualizer takes the reconstructed ComponentAnalysis object; rachis
        # runs this transformer automatically when the action is invoked, so we
        # apply it directly when calling the function under test.
        cls.mfa_component_analysis = _dirfmt_to_component_analysis(
            ComponentAnalysisDirFmt(
                instance.get_data_path("mfa/mfa_vis_results"),
                mode="r",
            )
        )
        cls.pca_component_analysis = _dirfmt_to_component_analysis(
            ComponentAnalysisDirFmt(
                str(
                    Path(__file__).parents[1]
                    / "types"
                    / "tests"
                    / "data"
                    / "component-analysis"
                    / "jsonl"
                    / "pca"
                ),
                mode="r",
            )
        )

    def _load_payload(self, output_dir):
        prefix = "window.COMPONENT_VISUALIZER_DATA = "
        data = Path(output_dir) / "data.js"
        payload = data.read_text(encoding="utf-8")
        self.assertTrue(payload.startswith(prefix))
        return json.loads(payload[len(prefix) :].rstrip(";\n"))

    def _assert_record_almost_equal(self, observed, expected):
        self.assertEqual(set(observed), set(expected))
        for key, expected_value in expected.items():
            if isinstance(expected_value, float):
                self.assertAlmostEqual(observed[key], expected_value)
            else:
                self.assertEqual(observed[key], expected_value)

    def _assert_records_almost_equal(self, observed, expected):
        self.assertEqual(len(observed), len(expected))
        for observed_record, expected_record in zip(observed, expected):
            self._assert_record_almost_equal(observed_record, expected_record)

    def _assert_component_arrays_almost_equal(self, observed, expected):
        # observed is an entity record with columnar value arrays; expected maps
        # each field name to the list of per-component values.
        for field, expected_values in expected.items():
            observed_values = observed[field]
            self.assertEqual(len(observed_values), len(expected_values))
            for observed_value, expected_value in zip(observed_values, expected_values):
                if isinstance(expected_value, float):
                    # Payload arrays are rounded to 6 decimals to shrink the
                    # embedded data, so compare below that precision.
                    self.assertAlmostEqual(observed_value, expected_value, places=5)
                else:
                    self.assertEqual(observed_value, expected_value)

    def test_plugin_registers_component_visualizer(self):
        self.assertIn("component_visualizer", self.plugin.visualizers)

    def test_component_visualizer_writes_assets_and_jsonl_payload(self):
        with tempfile.TemporaryDirectory() as output_dir:
            component_visualizer(
                output_dir, self.mfa_component_analysis, "mfa", self.metadata
            )

            output_path = Path(output_dir)
            for filename in (
                "index.html",
                "style.css",
                "app.js",
                "plotly-basic-2.35.2.min.js",
                "plotly-basic-2.35.2.min.js.LICENSE.txt",
                "data.js",
            ):
                self.assertTrue((output_path / filename).exists())

            index_html = (output_path / "index.html").read_text(encoding="utf-8")
            app_js = (output_path / "app.js").read_text(encoding="utf-8")
            style_css = (output_path / "style.css").read_text(encoding="utf-8")
            visualization_assets = index_html + app_js

            for expected_text in (
                "component-analysis sample coordinate table",
                "component-analysis percentage-of-variance result table",
                "component-analysis cumulative-percentage-of-variance result table",
                "MFA group coordinate result table",
                "MFA partial correlation result table",
                "component-analysis JSONL result tables",
                "sqrt(x^2 + y^2)",
            ):
                self.assertIn(expected_text, visualization_assets)

            self.assertIn("payload.samples", app_js)
            self.assertIn("payload.features", app_js)
            self.assertIn("payload.groups", app_js)
            self.assertIn("function buildVarianceHoverText(component)", app_js)
            self.assertIn(
                "`Cumulative explained variance: ${formatValue("
                "component.cumulative_variance_explained)}%`",
                app_js,
            )
            self.assertIn("customdata: components.map(buildVarianceHoverText)", app_js)
            self.assertIn("const analysisLabel = analysisType.toUpperCase();", app_js)
            self.assertIn("const isMfa = analysisType === 'mfa';", app_js)
            self.assertIn("document.querySelectorAll('.mfa-only')", app_js)
            self.assertIn("source.entity === 'feature' && isMfa", app_js)
            self.assertIn("feature.variable", app_js)
            self.assertIn('id="sample-details"', index_html)
            self.assertIn("Click a sample to view details.", index_html)
            self.assertIn("selectedSampleId: null,", app_js)
            self.assertIn("graphDiv.on('plotly_click'", app_js)
            self.assertIn("renderSampleDetailsPanel();", app_js)
            self.assertIn("state.selectedSampleId === sampleId", app_js)
            self.assertIn("function toggleSelectedSample(sampleId", app_js)
            self.assertIn("function scrollToSamplePlot()", app_js)
            self.assertIn("scrollIntoView({", app_js)
            self.assertIn("applySamplePlotSquareDataArea(layout);", app_js)
            self.assertIn("function applySamplePlotSquareDataArea(layout)", app_js)
            self.assertIn("layout.width = width;", app_js)
            self.assertIn("layout.height = height;", app_js)
            self.assertIn(
                "const layoutRect = samplePlotLayout.getBoundingClientRect();", app_js
            )
            self.assertIn("const shellHorizontalBorder =", app_js)
            self.assertIn("const shellHeight = height + shellVerticalBorder;", app_js)
            self.assertIn("samplePlotShell.style.width = `${shellWidth}px`;", app_js)
            self.assertIn("samplePlotShell.style.height = `${shellHeight}px`;", app_js)
            self.assertIn("samplePlotLayout.style.setProperty", app_js)
            self.assertIn("--sample-plot-height", app_js)
            self.assertIn("text: samples.map(buildSampleHoverText),", app_js)
            self.assertIn("hovertemplate: '%{text}<extra></extra>'", app_js)
            self.assertIn("function buildSampleHoverText(sample)", app_js)
            self.assertIn("function buildSampleNameCell(row)", app_js)
            self.assertIn(
                "toggleSelectedSample(row.fullName, { scrollToPlot: true });", app_js
            )
            self.assertIn(".sample-name-button", style_css)
            self.assertIn(
                "dimLine(state.xDimension, componentField(feature, "
                "state.xDimension, 'coordinate'), 'coordinate')",
                app_js,
            )
            self.assertIn(
                "dimLine(state.xDimension, componentField(feature, "
                "state.xDimension, 'correlation'), 'correlation')",
                app_js,
            )
            self.assertIn("dimContributionLine(state.xDimension", app_js)
            self.assertIn("`Plane magnitude coordinates: ", app_js)
            self.assertIn("`Plane magnitude correlation: ", app_js)
            self.assertIn("filter-row filter-row-coordinate-control", app_js)
            self.assertIn("function buildSampleMetricsTable(sample)", app_js)
            self.assertIn("buildSampleMetricRow('coordinate'", app_js)
            self.assertIn("buildSampleMetricRow('contribution'", app_js)
            self.assertIn("buildSampleMetricRow('cos2'", app_js)
            self.assertIn("formatPercent(componentField(sample", app_js)
            self.assertIn("function buildSampleMetadataTable(sample)", app_js)
            self.assertIn("container.appendChild(buildSampleCoordinatesRow());", app_js)
            self.assertIn("function buildSampleCoordinatesRow()", app_js)
            self.assertIn("const hasMetadata = metadataColumns.length > 0;", app_js)
            self.assertIn("function applyMetadataAvailability()", app_js)
            self.assertIn("element.hidden = !hasMetadata;", app_js)
            self.assertIn("if (!hasMetadata) {", app_js)
            self.assertIn("[hidden]", style_css)
            self.assertIn("display: none !important;", style_css)
            self.assertIn(".sample-plot-layout-no-metadata", style_css)
            self.assertIn("border-radius: 10px;", style_css)
            self.assertIn(".filter-row-coordinate-control", style_css)
            self.assertIn("grid-column: 1 / -1 !important;", style_css)
            self.assertIn(".sample-plot-layout", style_css)
            self.assertIn("grid-template-columns: minmax(0, 1fr) 280px;", style_css)
            self.assertIn("align-items: start;", style_css)
            self.assertIn("width: max-content;", style_css)
            self.assertIn("overflow: hidden;", style_css)
            self.assertIn("#sample-plot", style_css)
            self.assertIn(".sample-details-panel", style_css)
            self.assertIn("width: 280px;", style_css)
            self.assertIn("height: var(--sample-plot-height, auto);", style_css)
            self.assertIn(
                "const className = index === 0 ? 'sample-details-name' : '';", app_js
            )
            self.assertIn(".sample-details-name", style_css)
            self.assertIn(".sample-details-table th,", style_css)
            self.assertIn("overflow-wrap: anywhere;", style_css)
            self.assertIn("sample.sample_id === state.selectedSampleId", app_js)
            self.assertIn("return 3;", app_js)
            self.assertNotIn("sample-hover-card", visualization_assets)
            self.assertNotIn("plotly_hover", app_js)
            self.assertNotIn("resize: horizontal", style_css)
            self.assertNotIn("updateSamplePlotResizeLimits", app_js)
            self.assertNotIn("https://cdn.plot.ly", index_html)

            payload = self._load_payload(output_dir)

        self.assertEqual(payload["analysis_type"], "mfa")
        self.assertNotIn("analysis_slug", payload)
        self.assertNotIn("analysis_label", payload)
        self.assertNotIn("default_x", payload)
        self.assertNotIn("default_y", payload)
        self.assertEqual(
            payload["dimensions"],
            [
                {
                    "component": 0,
                    "label": "Dim 1",
                    "axis_title": "Dim 1 (60.0% explained)",
                    "eigenvalue": 1.4535736427000001,
                    "variance_explained": 60.025414068,
                    "cumulative_variance_explained": 60.025414068,
                },
                {
                    "component": 1,
                    "label": "Dim 2",
                    "axis_title": "Dim 2 (34.2% explained)",
                    "eigenvalue": 0.827848643,
                    "variance_explained": 34.1860612503,
                    "cumulative_variance_explained": 94.2114753183,
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
        self.assertEqual(metadata_columns["age"]["max"], 41.0)
        self.assertEqual(
            {
                "sample_id": payload["samples"][0]["sample_id"],
                "metadata": payload["samples"][0]["metadata"],
            },
            {
                "sample_id": "s1",
                "metadata": {
                    "body_site": "gut",
                    "cohort": "control",
                    "age": 23.0,
                    "bmi": 20.5,
                },
            },
        )

    def test_component_visualizer_accepts_missing_metadata(self):
        with tempfile.TemporaryDirectory() as output_dir:
            component_visualizer(output_dir, self.mfa_component_analysis, "mfa")

            output_path = Path(output_dir)
            for filename in (
                "index.html",
                "style.css",
                "app.js",
                "plotly-basic-2.35.2.min.js",
                "plotly-basic-2.35.2.min.js.LICENSE.txt",
                "data.js",
            ):
                self.assertTrue((output_path / filename).exists())

            payload = self._load_payload(output_dir)

        self.assertEqual(payload["metadata_columns"], [])
        self.assertGreater(len(payload["samples"]), 0)
        self.assertTrue(all(sample["metadata"] == {} for sample in payload["samples"]))
        self.assertEqual(payload["samples"][0]["sample_id"], "s1")
        self._assert_component_arrays_almost_equal(
            payload["samples"][0],
            {
                "coordinate": [-0.4561011643, 0.1336687224],
                "contribution": [0.028623011, 0.0043165686],
                "cos2": [0.390501218, 0.0335397349],
            },
        )

    def test_component_visualizer_payload_uses_domain_view_model_records(self):
        with tempfile.TemporaryDirectory() as output_dir:
            component_visualizer(
                output_dir, self.mfa_component_analysis, "mfa", self.metadata
            )
            payload = self._load_payload(output_dir)

        self.assertEqual(
            [entry["group"] for entry in payload["groups"]],
            ["chemical", "physical"],
        )
        self.assertEqual(payload["samples"][0]["sample_id"], "s1")
        self._assert_component_arrays_almost_equal(
            payload["samples"][0],
            {
                "coordinate": [-0.4561011643, 0.1336687224],
                "contribution": [0.028623011, 0.0043165686],
                "cos2": [0.390501218, 0.0335397349],
            },
        )

        self.assertEqual(
            {
                "group": payload["features"][0]["group"],
                "variable": payload["features"][0]["variable"],
            },
            {"group": "chemical", "variable": "shared"},
        )
        self._assert_component_arrays_almost_equal(
            payload["features"][0],
            {
                "coordinate": [0.857465367, 0.343608628],
                "correlation": [0.857465367, 0.343608628],
                "contribution": [0.2821391966, 0.0795507848],
                "cos2": [0.7352468557, 0.1180668893],
            },
        )

        self.assertEqual(
            {
                "sample_id": payload["partial_samples"][0]["sample_id"],
                "group": payload["partial_samples"][0]["group"],
            },
            {"sample_id": "s1", "group": "chemical"},
        )
        self._assert_component_arrays_almost_equal(
            payload["partial_samples"][0],
            {"coordinate": [-0.6790144466, -0.3604041713]},
        )

        self.assertEqual(payload["groups"][0]["group"], "chemical")
        self._assert_component_arrays_almost_equal(
            payload["groups"][0],
            {
                "coordinate": [0.8458788329, 0.1479904694],
                "contribution": [0.5819304974, 0.178765129],
                "cos2": [0.7060801021, 0.0216125073],
            },
        )

        self.assertEqual(
            {
                "group": payload["partial_axes"][0]["group"],
                "partial_component": payload["partial_axes"][0]["partial_component"],
            },
            {"group": "chemical", "partial_component": 0},
        )
        self._assert_component_arrays_almost_equal(
            payload["partial_axes"][0],
            {
                "correlation": [0.9196109002, 0.3841112645],
                "contribution": [0.5817966032, 0.1782227521],
            },
        )

    def test_pca_visualizer_writes_payload_without_mfa_only_data(self):
        with tempfile.TemporaryDirectory() as output_dir:
            component_visualizer(output_dir, self.pca_component_analysis, "pca")

            output_path = Path(output_dir)
            for filename in (
                "index.html",
                "style.css",
                "app.js",
                "plotly-basic-2.35.2.min.js",
                "plotly-basic-2.35.2.min.js.LICENSE.txt",
                "data.js",
            ):
                self.assertTrue((output_path / filename).exists())

            app_js = (output_path / "app.js").read_text(encoding="utf-8")
            self.assertIn("if (isMfa) {", app_js)
            self.assertIn("source.entity === 'feature' && isMfa", app_js)
            self.assertIn("isMfa ? feature.group : 'Features'", app_js)
            payload = self._load_payload(output_dir)

        self.assertEqual(payload["analysis_type"], "pca")
        self.assertNotIn("analysis_slug", payload)
        self.assertNotIn("analysis_label", payload)
        self.assertEqual(payload["groups"], [])
        self.assertEqual(payload["partial_samples"], [])
        self.assertEqual(payload["partial_axes"], [])
        self.assertGreater(len(payload["features"]), 0)
        self.assertIn("eigenvalue", payload["dimensions"][0])
        self.assertNotIn("group", payload["features"][0])
        self.assertIn("variable", payload["features"][0])
