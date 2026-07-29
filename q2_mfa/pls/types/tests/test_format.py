# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import shutil
import tempfile
from pathlib import Path

from q2_types.tabular import TableJSONLFileFormat
from rachis.plugin.model import ValidationError
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import PLSAnalysisDirFmt


class TestPLSAnalysisDirFmt(TestPluginBase):
    package = "q2_mfa.pls.types.tests"

    @classmethod
    def setUpClass(cls):
        helper = cls()
        cls.fixture_dir = Path(helper.get_data_path("pls-analysis/complete"))

    def test_complete_fixture_validates_and_iterates_collections(self):
        fmt = PLSAnalysisDirFmt(self.fixture_dir, mode="r")

        fmt.validate()

        expected_blocks = {
            "metabolomics",
            "microbiome",
            "y",
        }
        for collection_name in (
            "loadings",
            "loadings_star",
            "variates",
            "prop_expl_var",
            "vip",
        ):
            collection = getattr(fmt, collection_name)
            observed_blocks = {
                path.stem for path, _ in collection.iter_views(TableJSONLFileFormat)
            }
            self.assertEqual(observed_blocks, expected_blocks)

    def test_loadings_star_collection_is_optional(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_dir = Path(temp_dir) / "fixture"
            shutil.copytree(self.fixture_dir, fixture_dir)
            for path in fixture_dir.glob("loadings_star/*.jsonl"):
                path.unlink()

            PLSAnalysisDirFmt(fixture_dir, mode="r").validate()

    def test_path_makers_use_the_output_first_layout(self):
        fmt = PLSAnalysisDirFmt()

        paths = {
            "loadings": fmt.loadings.path_maker(block="microbiome"),
            "loadings_star": fmt.loadings_star.path_maker(block="microbiome"),
            "variates": fmt.variates.path_maker(block="microbiome"),
            "prop_expl_var": fmt.prop_expl_var.path_maker(block="microbiome"),
            "vip": fmt.vip.path_maker(block="microbiome"),
            "ave": fmt.ave.path_maker(table="inner"),
            "crit": fmt.crit.path_maker(),
        }

        observed_paths = {
            name: path.relative_to(fmt.path) for name, path in paths.items()
        }
        self.assertEqual(
            observed_paths,
            {
                "loadings": Path("loadings/microbiome.jsonl"),
                "loadings_star": Path("loadings_star/microbiome.jsonl"),
                "variates": Path("variates/microbiome.jsonl"),
                "prop_expl_var": Path("prop_expl_var/microbiome.jsonl"),
                "vip": Path("vip/microbiome.jsonl"),
                "ave": Path("ave/inner.jsonl"),
                "crit": Path("crit/criterion.jsonl"),
            },
        )

    def test_required_collections_need_at_least_one_member(self):
        collection_paths = {
            "loadings": "loadings/*.jsonl",
            "variates": "variates/*.jsonl",
            "prop_expl_var": "prop_expl_var/*.jsonl",
            "vip": "vip/*.jsonl",
        }
        for collection_name, pattern in collection_paths.items():
            with (
                self.subTest(collection_name=collection_name),
                tempfile.TemporaryDirectory() as temp_dir,
            ):
                fixture_dir = Path(temp_dir) / "fixture"
                shutil.copytree(self.fixture_dir, fixture_dir)
                for path in fixture_dir.glob(pattern):
                    path.unlink()

                with self.assertRaises(ValidationError):
                    PLSAnalysisDirFmt(fixture_dir, mode="r").validate()
