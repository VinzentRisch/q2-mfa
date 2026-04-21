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

from q2_types.ordination import OrdinationFormat, PCoAResults
from rachis import Artifact, Metadata
from rachis.core.type import Properties
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults

from q2_mfa._mfa_visualizer import mfa_visualizer


class TestMFAVisualizer(TestPluginBase):
    package = "q2_mfa.tests"

    @classmethod
    def setUpClass(cls):
        instance = cls()
        cls.ordination = instance._load_ordination("mfa_vis/ord_global.ordination")
        cls.single_axis_ordination = instance._load_ordination(
            "mfa_vis/ord_group_a.ordination"
        )
        cls.metadata = Metadata.load(
            instance.get_data_path("mfa_vis/sample_metadata.tsv")
        )

    @classmethod
    def _load_ordination(cls, path):
        artifact = Artifact.import_data(
            PCoAResults % Properties("mfa"),
            cls().get_data_path(path),
            view_type=OrdinationFormat,
        )
        return artifact.view(OrdinationResults)

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
            mfa_visualizer(output_dir, self.ordination, self.metadata)

            for filename in (
                "index.html",
                "graphs.html",
                "style.css",
                "app.js",
                "data.js",
            ):
                self.assertTrue((Path(output_dir) / filename).exists())

            payload = self._load_payload(output_dir)

        self.assertEqual(payload["default_tab"], "graphs")
        self.assertEqual(payload["default_x"], "Dim 1")
        self.assertEqual(payload["default_y"], "Dim 2")
        self.assertEqual(
            payload["tabs"],
            [{"url": "graphs.html", "title": "Graphs"}],
        )
        self.assertEqual(
            [dimension["label"] for dimension in payload["dimensions"]],
            ["Dim 1", "Dim 2"],
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

    def test_mfa_visualizer_requires_at_least_two_dimensions(self):
        with tempfile.TemporaryDirectory() as output_dir:
            with self.assertRaisesRegex(
                ValueError, "requires at least two sample dimensions"
            ):
                mfa_visualizer(output_dir, self.single_axis_ordination, self.metadata)
