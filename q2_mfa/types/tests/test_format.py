# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from rachis.core.exceptions import ValidationError
from rachis.plugin.testing import TestPluginBase

from q2_mfa.types import MFAResultsDirFmt, NumericTSVFormat


class TestMFAFormats(TestPluginBase):
    package = "q2_mfa.types.tests"

    def test_numeric_tsv_format_ok(self):
        fmt = NumericTSVFormat(
            self.get_data_path("prince-wide.tsv"),
            mode="r",
        )
        fmt.validate()

    def test_numeric_tsv_format_ok_non_finite_values(self):
        fmt = NumericTSVFormat(
            self.get_data_path("prince-wide-non-finite-values.tsv"),
            mode="r",
        )
        fmt.validate()

    def test_numeric_tsv_format_ok_empty_values(self):
        fmt = NumericTSVFormat(
            self.get_data_path("prince-wide-empty-values.tsv"),
            mode="r",
        )
        fmt.validate()

    def test_numeric_tsv_format_error_header(self):
        fmt = NumericTSVFormat(
            self.get_data_path("prince-wide-broken-header.tsv"),
            mode="r",
        )
        with self.assertRaisesRegex(ValidationError, "Invalid header"):
            fmt.validate()

    def test_numeric_tsv_format_error_values(self):
        fmt = NumericTSVFormat(
            self.get_data_path("prince-wide-broken-values.tsv"),
            mode="r",
        )
        with self.assertRaisesRegex(ValidationError, "Line 3 has 2 columns"):
            fmt.validate()

    def test_numeric_tsv_format_error_no_value_columns(self):
        fmt = NumericTSVFormat(
            self.get_data_path("prince-wide-no-values.tsv"),
            mode="r",
        )
        with self.assertRaisesRegex(ValidationError, "at least 1"):
            fmt.validate()

    def test_numeric_tsv_format_error_non_numeric_value(self):
        fmt = NumericTSVFormat(
            self.get_data_path("prince-wide-non-numeric-value.tsv"),
            mode="r",
        )
        with self.assertRaisesRegex(
            ValidationError,
            "Numeric TSV value columns must be numeric.",
        ):
            fmt.validate()

    def test_mfa_results_directory_format_ok(self):
        fmt = MFAResultsDirFmt(self.get_data_path("mfa-results"), mode="r")
        fmt.validate()
