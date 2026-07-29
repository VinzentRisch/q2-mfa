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

        expected_paths = {
            Path("metabolomics"),
            Path("microbiome"),
            Path("y"),
        }
        for collection_name in PLSAnalysisDirFmt._fields:
            collection = getattr(fmt, collection_name)
            observed_paths = {
                path.parent for path, _ in collection.iter_views(TableJSONLFileFormat)
            }
            self.assertEqual(observed_paths, expected_paths)

    def test_loadings_star_collection_is_optional(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_dir = Path(temp_dir) / "fixture"
            shutil.copytree(self.fixture_dir, fixture_dir)
            for path in fixture_dir.glob("*/loadings_star.jsonl"):
                path.unlink()

            PLSAnalysisDirFmt(fixture_dir, mode="r").validate()

    def test_required_collections_need_at_least_one_member(self):
        for collection_name in ("loadings", "variates", "prop_expl_var", "vip"):
            with (
                self.subTest(collection_name=collection_name),
                tempfile.TemporaryDirectory() as temp_dir,
            ):
                fixture_dir = Path(temp_dir) / "fixture"
                shutil.copytree(self.fixture_dir, fixture_dir)
                for path in fixture_dir.glob(f"*/{collection_name}.jsonl"):
                    path.unlink()

                with self.assertRaises(ValidationError):
                    PLSAnalysisDirFmt(fixture_dir, mode="r").validate()
