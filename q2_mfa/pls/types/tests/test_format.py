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

from rachis.plugin.model import ValidationError
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import PLSAnalysisDirFmt


class TestPLSAnalysisDirFmt(TestPluginBase):
    package = "q2_mfa.pls.types.tests"

    @classmethod
    def setUpClass(cls):
        helper = cls()
        cls.fixture_dir = Path(helper.get_data_path("pls-analysis/complete"))

    def test_complete_fixture_validates(self):
        fmt = PLSAnalysisDirFmt(self.fixture_dir, mode="r")

        fmt.validate()

    def test_optional_tables_are_optional(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_dir = Path(temp_dir) / "fixture"
            shutil.copytree(self.fixture_dir, fixture_dir)
            for table_name in (
                "loadings_star.jsonl",
                "vip.jsonl",
                "ave.jsonl",
                "criterion.jsonl",
                "feature_stability.jsonl",
            ):
                path = fixture_dir / table_name
                path.unlink()

            PLSAnalysisDirFmt(fixture_dir, mode="r").validate()

    def test_required_tables_must_exist(self):
        for table_name in (
            "loadings.jsonl",
            "variates.jsonl",
            "prop_expl_var.jsonl",
            "auc.jsonl",
            "ncomp_selection_weighted_vote_error_rate.jsonl",
            "final_model_weighted_vote_error_rate.jsonl",
        ):
            with (
                self.subTest(table_name=table_name),
                tempfile.TemporaryDirectory() as temp_dir,
            ):
                fixture_dir = Path(temp_dir) / "fixture"
                shutil.copytree(self.fixture_dir, fixture_dir)
                (fixture_dir / table_name).unlink()

                with self.assertRaises(ValidationError):
                    PLSAnalysisDirFmt(fixture_dir, mode="r").validate()
