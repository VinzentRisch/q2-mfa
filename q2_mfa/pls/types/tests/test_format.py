# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
# ----------------------------------------------------------------------------
import shutil
import tempfile
from pathlib import Path

from rachis.plugin.model import ValidationError
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import PLSTuneComponentsDirFmt


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
            "error_rate_weighted.jsonl",
            "error_rate_majority.jsonl",
            "choice_matrix_weighted.jsonl",
            "choice_matrix_majority.jsonl",
        ):
            with self.subTest(
                table_name=table_name
            ), tempfile.TemporaryDirectory() as temp_dir:
                fixture_dir = Path(temp_dir) / "fixture"
                shutil.copytree(self.fixture_dir, fixture_dir)
                (fixture_dir / table_name).unlink()

                with self.assertRaises(ValidationError):
                    PLSTuneComponentsDirFmt(fixture_dir, mode="r").validate()
