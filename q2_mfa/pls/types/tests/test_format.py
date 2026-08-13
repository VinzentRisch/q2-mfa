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

from q2_mfa.pls import PLSFitDirFmt, PLSTuneComponentsDirFmt, PLSTuneFeaturesDirFmt


class TestPLSFitDirFmt(TestPluginBase):
    package = "q2_mfa.pls.types.tests"

    @classmethod
    def setUpClass(cls):
        helper = cls()
        cls.fixture_dir = Path(helper.get_data_path("pls-analysis/complete"))

    def test_complete_fixture_validates(self):
        PLSFitDirFmt(self.fixture_dir, mode="r").validate()

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
                (fixture_dir / table_name).unlink()

            PLSFitDirFmt(fixture_dir, mode="r").validate()

    def test_required_tables_must_exist(self):
        for table_name in (
            "loadings.jsonl",
            "variates.jsonl",
            "prop_expl_var.jsonl",
            "auc.jsonl",
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
                    PLSFitDirFmt(fixture_dir, mode="r").validate()


class TestPLSTuneComponentsDirFmt(TestPluginBase):
    package = "q2_mfa.pls.types.tests"

    @classmethod
    def setUpClass(cls):
        helper = cls()
        cls.fixture_dir = Path(helper.get_data_path("pls-tune-components/complete"))

    def test_complete_fixture_validates(self):
        PLSTuneComponentsDirFmt(self.fixture_dir, mode="r").validate()

    def test_required_tables_must_exist(self):
        for table_name in (
            "ncomp_selection_vote_error_rate.jsonl",
            "ncomp_selection_choice_matrix.jsonl",
        ):
            with (
                self.subTest(table_name=table_name),
                tempfile.TemporaryDirectory() as temp_dir,
            ):
                fixture_dir = Path(temp_dir) / "fixture"
                shutil.copytree(self.fixture_dir, fixture_dir)
                (fixture_dir / table_name).unlink()

                with self.assertRaises(ValidationError):
                    PLSTuneComponentsDirFmt(fixture_dir, mode="r").validate()


class TestPLSTuneFeaturesDirFmt(TestPluginBase):
    package = "q2_mfa.pls.types.tests"

    @classmethod
    def setUpClass(cls):
        helper = cls()
        cls.fixture_dir = Path(helper.get_data_path("pls-tune-features/complete"))

    def test_complete_fixture_validates(self):
        PLSTuneFeaturesDirFmt(self.fixture_dir, mode="r").validate()

    def test_required_table_must_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_dir = Path(temp_dir) / "fixture"
            shutil.copytree(self.fixture_dir, fixture_dir)
            (fixture_dir / "feature_selection_error_rate.jsonl").unlink()

            with self.assertRaises(ValidationError):
                PLSTuneFeaturesDirFmt(fixture_dir, mode="r").validate()

    def test_extra_file_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_dir = Path(temp_dir) / "fixture"
            shutil.copytree(self.fixture_dir, fixture_dir)
            shutil.copy(
                fixture_dir / "feature_selection_error_rate.jsonl",
                fixture_dir / "extra.jsonl",
            )

            with self.assertRaises(ValidationError):
                PLSTuneFeaturesDirFmt(fixture_dir, mode="r").validate()
