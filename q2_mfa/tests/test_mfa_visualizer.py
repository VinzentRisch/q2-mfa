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
from q2_mfa.types import ComponentAnalysisDirFmt


class TestMFAVisualizer(TestPluginBase):
    package = "q2_mfa.tests"

    @classmethod
    def setUpClass(cls):
        instance = cls()
        cls.metadata = Metadata.load(
            instance.get_data_path("mfa_vis/sample_metadata.tsv")
        )
        cls.mfa_results = ComponentAnalysisDirFmt(
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
            self.assertIn('id="feature-name-tooltip"', index_html)
            self.assertIn('id="download-feature-table"', index_html)
            self.assertIn('aria-label="Features"', index_html)
            self.assertIn("Features", index_html)
            self.assertNotIn('id="feature-source"', index_html)
            self.assertIn(
                '<label for="top-feature-count">Number of features</label>',
                index_html,
            )
            self.assertIn('<label for="color-by">Color by</label>', index_html)
            self.assertIn(
                '<input id="top-feature-count" type="number" min="1" '
                'max="100" step="1" value="10">',
                index_html,
            )
            self.assertIn(
                '<label for="feature-scale">Feature scale</label>',
                index_html,
            )
            self.assertIn(
                '<input id="feature-scale" type="number" min="1" '
                'step="1" value="1">',
                index_html,
            )
            self.assertIn('<label for="font-family">Font</label>', index_html)
            self.assertIn('<select id="font-family"></select>', index_html)
            self.assertIn(
                '<label for="point-size-scale">Point size</label>',
                index_html,
            )
            self.assertIn(
                '<input id="point-size-scale" type="number" min="0.5" '
                'max="1.5" step="0.1" value="1">',
                index_html,
            )
            self.assertIn(
                '<label for="point-opacity">Point opacity</label>', index_html
            )
            self.assertIn(
                '<input id="point-opacity" type="number" min="0.1" '
                'max="1" step="0.05" value="0.9">',
                index_html,
            )
            self.assertIn('<label for="size-by">Size by</label>', index_html)
            self.assertIn('<select id="size-by"></select>', index_html)
            self.assertIn(
                '<label class="toggle-option" for="show-point-border">',
                index_html,
            )
            self.assertIn(
                '<input id="show-point-border" type="checkbox" checked>',
                index_html,
            )
            self.assertIn("<span>Point border</span>", index_html)
            self.assertIn(
                '<label class="toggle-option" for="show-full-feature-labels">',
                index_html,
            )
            self.assertIn(
                '<input id="show-full-feature-labels" type="checkbox">',
                index_html,
            )
            self.assertIn("<span>Full feature labels</span>", index_html)
            self.assertIn(
                '<label class="toggle-option" for="show-feature-scale-circle">',
                index_html,
            )
            self.assertIn(
                '<input id="show-feature-scale-circle" type="checkbox">',
                index_html,
            )
            self.assertIn("<span>Scale circle</span>", index_html)
            self.assertIn('id="filter-controls"', index_html)
            self.assertNotIn('id="filter-by"', index_html)
            self.assertIn('class="plot-shell plot-shell-main"', index_html)
            app_js = (Path(output_dir) / "app.js").read_text(encoding="utf-8")
            visualization_assets = index_html + app_js
            for expected_tooltip_text in (
                "visible sample scores from ordination.txt",
                "partial coordinates from partial-sample-coordinates.tsv",
                "global sample scores from ordination.txt",
                "feature correlations from feature-correlations.tsv",
                "feature coordinates from ordination.txt",
                "sqrt(x^2 + y^2)",
                "proportion explained values stored in ordination.txt",
                "running total calculated from the component proportion "
                "explained values in ordination.txt",
                "group coordinates from group-coordinates.tsv",
                "contribution values from group-contributions.tsv",
                "cos2 values from group-cosine-similarities.tsv",
                "partial axis correlations from partial-correlations.tsv",
                "Ranks all features from the selected feature source",
                "Features are ordered by plane magnitude",
                "For correlations, it marks correlation magnitude 1 after scaling",
            ):
                self.assertIn(expected_tooltip_text, visualization_assets)
            self.assertNotIn('data-feature-sort="rank"', index_html)
            self.assertNotIn("<span>Rank</span>", index_html)
            self.assertIn('<th aria-sort="descending">', index_html)
            for sort_key in ("feature_name", "group", "x", "y", "rankingScore"):
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
            self.assertIn(".filter-row {\n  display: grid;", style_css)
            self.assertNotIn(".control-group-feature-source", style_css)
            self.assertIn(
                "grid-template-columns: repeat(12, minmax(0, 1fr));", style_css
            )
            self.assertIn(".control-group-x-dimension {\n  grid-column: 1;", style_css)
            self.assertIn(".control-group-y-dimension {\n  grid-column: 2;", style_css)
            self.assertIn(
                ".control-group-color-by {\n  grid-column: 3 / span 2;", style_css
            )
            self.assertIn(
                ".control-group-color-palette {\n  grid-column: 5 / span 2;", style_css
            )
            self.assertIn(
                ".control-group-size-by {\n  grid-column: 7 / span 2;", style_css
            )
            self.assertIn(".control-group-font-family {\n  grid-column: 9;", style_css)
            self.assertIn(
                ".control-group-point-size {\n  grid-column: 11;\n  grid-row: 1;",
                style_css,
            )
            self.assertIn(
                ".control-group-barycenter {\n  grid-column: 9 / span 2;", style_css
            )
            self.assertIn(".control-group-font-size {\n  grid-column: 10;", style_css)
            self.assertIn(
                ".control-group-full-feature-labels {\n  grid-column: 7 / span 2;",
                style_css,
            )
            self.assertIn(
                ".control-group-scale-circle {\n  grid-column: 5 / span 2;", style_css
            )
            self.assertIn(
                ".control-group-point-opacity {\n  grid-column: 12;", style_css
            )
            self.assertIn(
                ".control-group-point-border {\n  grid-column: 11 / span 2;", style_css
            )
            self.assertIn(
                ".control-group-filters {\n  grid-column: 1 / span 12;\n  grid-row: 3;",
                style_css,
            )
            self.assertIn(
                ".control-panel > .control-group {\n    grid-column: auto;", style_css
            )
            self.assertIn(".toggle-option-with-select select {", style_css)
            self.assertIn("  border: 0;", style_css)
            self.assertIn("  background: transparent;", style_css)
            self.assertIn(".filter-add {", style_css)
            self.assertIn(".filter-remove {", style_css)
            self.assertIn("resize: horizontal;", style_css)
            self.assertIn("max-width: 100%;", style_css)
            self.assertIn("container-type: inline-size;", style_css)
            self.assertIn("height: calc(100cqw - 34px);", style_css)
            self.assertNotIn(".plot-shell-main::after", style_css)
            self.assertNotIn("height: 640px;", style_css)

            self.assertIn("function bindSamplePlotResizeObserver()", app_js)
            self.assertIn("new ResizeObserver", app_js)
            self.assertIn("Plotly.Plots.resize('sample-plot')", app_js)
            self.assertIn("const SCIENTIFIC_FONTS = [", app_js)
            for font_name in (
                "Arial",
                "Helvetica",
                "Times New Roman",
                "Georgia",
                "Garamond",
                "Palatino",
                "Cambria",
                "Calibri",
                "Verdana",
                "Computer Modern",
            ):
                self.assertIn(f"label: '{font_name}'", app_js)
            self.assertIn("fontFamily: SCIENTIFIC_FONTS[0].family,", app_js)
            self.assertIn(
                "fontFamily.add(new Option(font.label, font.family));", app_js
            )
            self.assertIn("fontFamily.value = state.fontFamily;", app_js)
            self.assertIn(
                "document.getElementById('font-family').addEventListener",
                app_js,
            )
            self.assertIn("state.fontFamily = event.target.value;", app_js)
            self.assertIn("function buildPlotFont(themeColors", app_js)
            self.assertIn("family: themeColors.fontFamily,", app_js)
            self.assertIn("family: state.fontFamily,", app_js)
            self.assertNotIn("IBM Plex", app_js)
            self.assertNotIn("Helvetica Neue", app_js)
            self.assertIn("function formatSampleLegendName(name, samples)", app_js)
            self.assertIn("return `${name} (n=${samples.length})`;", app_js)
            self.assertIn("name: formatSampleLegendName(name, samples),", app_js)
            self.assertIn("showSampleScores: true,", app_js)
            self.assertIn(
                "buildOverlayToggle(\n      'Sample scores',\n"
                "      state.showSampleScores,",
                app_js,
            )
            self.assertIn(
                "state.showSampleScores = checked;",
                app_js,
            )
            self.assertIn(
                "function buildSampleScoreTraces(samples, colorColumn)", app_js
            )
            self.assertIn("if (!state.showSampleScores) {\n    return [];", app_js)
            self.assertIn("filters: [createDefaultSampleFilter()],", app_js)
            self.assertIn("function createDefaultSampleFilter()", app_js)
            self.assertIn("function buildSampleFilterRow(filter, index)", app_js)
            self.assertIn("function buildSampleMetadataSelect(filter)", app_js)
            self.assertIn("function buildFilterValueControls(filter)", app_js)
            self.assertIn("function buildFilterRemoveButton(index)", app_js)
            self.assertIn("state.filters.push(createDefaultSampleFilter());", app_js)
            self.assertIn("state.filters.splice(index, 1);", app_js)
            self.assertIn("function samplePassesFilter(sample, filter)", app_js)
            self.assertIn("function getAllowedGroups(target)", app_js)
            self.assertIn("getAllowedGroups('features')", app_js)
            self.assertIn("getAllowedGroups('partial_samples')", app_js)
            self.assertIn("Symbols: {", app_js)
            self.assertIn(
                "symbols: ['square', 'triangle-up', 'circle', 'x', 'star'],", app_js
            )
            self.assertIn("function isColorPaletteAvailable(paletteName)", app_js)
            self.assertIn("function getCategoricalLevelCount(colorColumn)", app_js)
            self.assertIn("function getCategoricalSymbols(count)", app_js)
            self.assertIn("symbol: options.symbol ?? 'circle',", app_js)
            self.assertIn(
                "name: formatSampleLegendName(colorColumn.name, numericSamples),",
                app_js,
            )
            self.assertIn(
                "text: formatSampleLegendName(colorColumn.name, numericSamples),",
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
            self.assertEqual(app_js.count("scaleanchor: 'y',"), 3)
            self.assertIn(
                "const sharedGridStep = computeSharedSampleGridStep(traces);", app_js
            )
            self.assertIn("function computeSharedSampleGridStep(traces)", app_js)
            self.assertIn("return computeNiceTickStep(span / 10);", app_js)
            self.assertIn("function computeNiceTickStep(rawStep)", app_js)
            self.assertEqual(app_js.count("tickmode: 'linear',"), 2)
            self.assertEqual(app_js.count("tick0: 0,"), 2)
            self.assertEqual(app_js.count("dtick: sharedGridStep,"), 2)
            self.assertGreaterEqual(app_js.count("constrain: 'domain',"), 4)
            self.assertNotIn("zeroline: false,", app_js)
            self.assertNotIn("zerolinewidth: 2,", app_js)
            self.assertIn("function computeSampleLegendRightMargin(traces)", app_js)
            self.assertIn(
                "const legendRightMargin = computeSampleLegendRightMargin(traces);",
                app_js,
            )
            self.assertIn(
                "margin: { t: 32, r: legendRightMargin, b: 78, l: 80 },", app_js
            )
            self.assertIn("SAMPLE_LEGEND_MAX_RIGHT_MARGIN = 420;", app_js)
            self.assertIn("const SAMPLE_NUMERIC_COLORBAR_Y = 1;", app_js)
            self.assertIn("const SAMPLE_NUMERIC_COLORBAR_LENGTH = 0.28;", app_js)
            self.assertIn("const SAMPLE_LEGEND_BELOW_COLORBAR_Y = 0.72;", app_js)
            self.assertIn("y: SAMPLE_NUMERIC_COLORBAR_Y,", app_js)
            self.assertIn("yanchor: 'top',", app_js)
            self.assertIn("len: SAMPLE_NUMERIC_COLORBAR_LENGTH,", app_js)
            self.assertIn("showlegend: false,", app_js)
            self.assertIn("function hasSampleNumericColorbar(traces)", app_js)
            self.assertIn(
                "const legendY = hasSampleNumericColorbar(traces) ? "
                "SAMPLE_LEGEND_BELOW_COLORBAR_Y : 1;",
                app_js,
            )
            self.assertIn("y: legendY,", app_js)
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
            self.assertIn("const FEATURE_SOURCE_OPTIONS = {", app_js)
            self.assertIn("const FEATURE_SCALE_CIRCLE_COLOR =", app_js)
            self.assertIn("topFeatureCount: 10,", app_js)
            self.assertIn("showFeatures: false,", app_js)
            self.assertIn("showFeatureScaleCircle: false,", app_js)
            self.assertIn("featureSource: 'coordinates',", app_js)
            self.assertIn("sizeBy: '',", app_js)
            self.assertIn("featureScale: 1,", app_js)
            self.assertIn("pointSizeScale: 1,", app_js)
            self.assertIn("pointOpacity: 0.9,", app_js)
            self.assertIn("showPointBorder: true,", app_js)
            self.assertIn(
                "document.getElementById('feature-scale').value = "
                "state.featureScale;",
                app_js,
            )
            self.assertIn(
                "document.getElementById('point-size-scale').value = "
                "state.pointSizeScale;",
                app_js,
            )
            self.assertIn(
                "document.getElementById('point-opacity').value = "
                "state.pointOpacity;",
                app_js,
            )
            self.assertIn(
                "document.getElementById('show-point-border').checked = "
                "state.showPointBorder;",
                app_js,
            )
            self.assertIn("sizeBy.add(new Option('None', ''));", app_js)
            self.assertIn(".filter((column) => column.type === 'numeric')", app_js)
            self.assertIn("sizeBy.add(new Option(column.name, column.name));", app_js)
            self.assertIn("sizeBy.value = state.sizeBy;", app_js)
            self.assertIn(
                "document.getElementById('show-feature-scale-circle').checked = "
                "state.showFeatureScaleCircle;",
                app_js,
            )
            self.assertIn(
                "document.getElementById('feature-scale').addEventListener",
                app_js,
            )
            self.assertIn(
                "document.getElementById('show-feature-scale-circle').addEventListener",
                app_js,
            )
            self.assertIn("function buildFeatureSourceToggle()", app_js)
            self.assertIn(
                "select.setAttribute('aria-label', 'Feature source');", app_js
            )
            self.assertIn(
                "select.add(new Option('Feature coord.', 'coordinates'));", app_js
            )
            self.assertIn(
                "select.add(new Option('Feature corr.', 'correlations'));", app_js
            )
            self.assertIn("select.value = state.featureSource;", app_js)
            self.assertIn("toggle.style.gridColumn = '1';", app_js)
            self.assertIn("groups.style.gridColumn = '2 / -1';", app_js)
            self.assertIn(
                "document.getElementById('point-size-scale').addEventListener",
                app_js,
            )
            self.assertIn(
                "document.getElementById('point-opacity').addEventListener",
                app_js,
            )
            self.assertIn(
                "document.getElementById('size-by').addEventListener",
                app_js,
            )
            self.assertIn(
                "document.getElementById('show-point-border').addEventListener",
                app_js,
            )
            self.assertIn("state.featureScale = Math.floor(nextValue);", app_js)
            self.assertIn("state.pointSizeScale = Math.min(nextValue, 1.5);", app_js)
            self.assertIn("state.pointOpacity = Math.min(nextValue, 1);", app_js)
            self.assertIn("state.sizeBy = event.target.value;", app_js)
            self.assertIn("state.showPointBorder = event.target.checked;", app_js)
            self.assertIn("function buildFeatureScaleCircleTrace()", app_js)
            self.assertIn("if (!state.showFeatureScaleCircle) {", app_js)
            self.assertIn("const radius = state.featureScale;", app_js)
            self.assertIn("function scalePointSize(baseSize)", app_js)
            self.assertIn("return baseSize * state.pointSizeScale;", app_js)
            self.assertIn("function getSamplePointSizes(samples, baseSize)", app_js)
            self.assertIn(
                "function getPartialPointSizes(groupEntries, baseSize)", app_js
            )
            self.assertIn(
                "function scaleMetadataPointSize(sample, sizeColumn, baseSize)", app_js
            )
            self.assertIn(
                "function scaleMetadataFractionPointSize(fraction, baseSize)", app_js
            )
            self.assertIn(
                "return scalePointSize(baseSize * (0.75 + 1.5 * fraction));", app_js
            )
            self.assertIn("function buildSizeLegendTraces()", app_js)
            self.assertIn("const sizeLegendTraces = buildSizeLegendTraces();", app_js)
            self.assertIn("...sizeLegendTraces,", app_js)
            self.assertIn("function buildSizeLegendHeaderTrace(name)", app_js)
            self.assertIn("mode: 'lines',", app_js)
            self.assertIn("`Size by: ${sizeColumn.name}`", app_js)
            self.assertIn("`min: ${formatValue(sizeColumn.min)}`", app_js)
            self.assertIn("`max: ${formatValue(sizeColumn.max)}`", app_js)
            self.assertIn("legendgroup: 'size-legend',", app_js)
            self.assertIn("x: [null],", app_js)
            self.assertIn("y: [null],", app_js)
            self.assertIn("scaleMetadataFractionPointSize(0, 8)", app_js)
            self.assertIn("scaleMetadataFractionPointSize(1, 8)", app_js)
            self.assertIn("function buildSamplePointMarkerLine(color, width)", app_js)
            self.assertIn(
                "return state.showPointBorder ? { color, width } : "
                "{ color, width: 0 };",
                app_js,
            )
            self.assertIn(
                "line: buildSamplePointMarkerLine(getThemeColors().markerLine, 1),",
                app_js,
            )
            self.assertIn(
                "line: buildSamplePointMarkerLine(themeColors.markerLine, 1),", app_js
            )
            self.assertIn("line: { color, width: 2 },", app_js)
            self.assertIn("opacity: state.pointOpacity,", app_js)
            self.assertIn("size: getPartialPointSizes(groupEntries, 6),", app_js)
            self.assertIn("size: getSamplePointSizes(samples, 8),", app_js)
            self.assertIn("size: getSamplePointSizes(numericSamples, 8),", app_js)
            self.assertIn("size: scalePointSize(9),", app_js)
            self.assertIn("column: 'rankingScore',", app_js)
            self.assertIn("direction: 'desc',", app_js)
            self.assertIn("showFullFeatureLabels: false,", app_js)
            self.assertIn(
                "document.getElementById('show-full-feature-labels').checked = "
                "state.showFullFeatureLabels;",
                app_js,
            )
            self.assertIn("function formatFeaturePlotLabel(featureName)", app_js)
            self.assertIn("function shortenTaxonomyFeatureName(featureName)", app_js)
            self.assertIn(".split(';')", app_js)
            self.assertIn(
                "const shortened = lastRank.replace(/^[kpcofgs]__/, '')", app_js
            )
            self.assertIn(
                "display_feature_name: "
                "shortenTaxonomyFeatureName(feature.feature_name),",
                app_js,
            )
            self.assertIn(
                "plot_feature_name: formatFeaturePlotLabel(feature.feature_name),",
                app_js,
            )
            self.assertIn("plotX: feature.x * state.featureScale,", app_js)
            self.assertIn("plotY: feature.y * state.featureScale,", app_js)
            self.assertIn("lineX.push(0, feature.plotX, null);", app_js)
            self.assertIn("x: groupFeatures.map((feature) => feature.plotX),", app_js)
            self.assertIn("anchorX: feature.plotX,", app_js)
            self.assertIn("${state.xDimension}: %{customdata[2]:.3f}<br>", app_js)
            self.assertIn("${state.yDimension}: %{customdata[3]:.3f}<br>", app_js)
            self.assertIn("feature.feature_name,\n        feature.group,", app_js)
            self.assertIn("feature.x,\n        feature.y,", app_js)
            self.assertIn("<b>${feature.feature_name}</b><br>", app_js)
            self.assertIn(
                "a.display_feature_name.localeCompare(b.display_feature_name)",
                app_js,
            )
            self.assertIn(
                "const features = getRankedFeatures(null, null);",
                app_js,
            )
            self.assertIn(".slice(0, MAX_FEATURE_OVERLAY_COUNT);", app_js)
            self.assertIn(
                "comparison = left.display_feature_name.localeCompare("
                "right.display_feature_name);",
                app_js,
            )
            self.assertIn(
                "const cell = buildFeatureTableCell("
                "feature.display_feature_name, 'feature-name-cell');",
                app_js,
            )
            self.assertIn(
                "function showFeatureNameTooltip(text, clientX, clientY)", app_js
            )
            self.assertIn(
                "function positionFeatureNameTooltip(clientX, clientY)", app_js
            )
            self.assertIn("function hideFeatureNameTooltip()", app_js)
            self.assertIn("cell.addEventListener('mouseenter'", app_js)
            self.assertIn("cell.addEventListener('focus'", app_js)
            self.assertIn("const tooltipText = feature.feature_name;", app_js)
            self.assertNotIn(
                "row.appendChild(buildFeatureTableCell(feature.rank", app_js
            )
            self.assertIn("text: feature.plot_feature_name,", app_js)
            self.assertIn("hoverinfo: 'skip'", app_js)
            self.assertNotIn(
                "customdata: labelPlacement.map((label) => label.hoverText)",
                app_js,
            )
            self.assertIn(
                "const groupLegend = `features:${state.featureSource}:${group}`;",
                app_js,
            )
            self.assertIn("name: `${group} (n=${groupFeatures.length})`,", app_js)
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
                "buildPlotLabelTrace(groupLabelPlacement, state.fontSize, {\n"
                "      legendgroup: groupLegend,",
                app_js,
            )
            self.assertIn("function getSortedFeatureTableRows()", app_js)
            self.assertIn("function buildFeatureValueColumnLabel(dimensionKey)", app_js)
            self.assertIn(
                "return "
                "`${dimensionsByKey[dimensionKey].label} ${state.featureSource}`;",
                app_js,
            )
            self.assertIn(
                "xHeading.textContent = "
                "buildFeatureValueColumnLabel(state.xDimension);",
                app_js,
            )
            self.assertIn(
                "yHeading.textContent = "
                "buildFeatureValueColumnLabel(state.yDimension);",
                app_js,
            )
            self.assertIn("function updateFeatureTableSort(button)", app_js)
            self.assertIn("function downloadFeatureTableTsv()", app_js)
            self.assertNotIn("'rank',", app_js)
            self.assertNotIn("'display_feature',", app_js)
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
        for feature in payload["feature_coordinates"]:
            self.assertEqual(set(feature["coords"]), {"Dim 1", "Dim 2"})
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
            payload["feature_coordinates"],
            [
                {
                    "feature_id": "A:feature-a",
                    "group": "A",
                    "feature_name": "feature-a",
                    "coords": {"Dim 1": 0.1, "Dim 2": 0.01},
                },
                {
                    "feature_id": "B:taxon:b:variant",
                    "group": "B",
                    "feature_name": "taxon:b:variant",
                    "coords": {"Dim 1": 0.3, "Dim 2": 0.03},
                },
                {
                    "feature_id": (
                        "B:k__Bacteria; p__Firmicutes; g__Blautia; "
                        "s__Blautia_wexlerae"
                    ),
                    "group": "B",
                    "feature_name": (
                        "k__Bacteria; p__Firmicutes; g__Blautia; " "s__Blautia_wexlerae"
                    ),
                    "coords": {"Dim 1": 0.4, "Dim 2": 0.04},
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
                {
                    "feature_id": (
                        "B:k__Bacteria; p__Firmicutes; g__Blautia; "
                        "s__Blautia_wexlerae"
                    ),
                    "group": "B",
                    "feature_name": (
                        "k__Bacteria; p__Firmicutes; g__Blautia; " "s__Blautia_wexlerae"
                    ),
                    "coords": {"Dim 1": 0.51, "Dim 2": 0.33},
                },
            ],
        )
