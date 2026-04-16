# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from rachis.core.exceptions import ValidationError
from rachis.plugin.testing import TestPluginBase

from q2_mfa.types import (
    GroupSummaryFormat,
    MFAResultsDirFmt,
    PartialAxesFormat,
    PartialScoresFormat,
)


class TestMFAFormats(TestPluginBase):
    package = "q2_mfa.types.tests"

    def test_partial_scores_format_ok(self):
        fmt = PartialScoresFormat(
            self.get_data_path("partial-scores.tsv"),
            mode="r",
        )
        fmt.validate(level="min")
        fmt.validate(level="max")

    def test_partial_scores_format_error_header(self):
        fmt = PartialScoresFormat(
            self.get_data_path("partial-scores-broken-header.tsv"),
            mode="r",
        )
        with self.assertRaisesRegex(ValidationError, "Invalid header"):
            fmt.validate()

    def test_partial_axes_format_ok(self):
        fmt = PartialAxesFormat(
            self.get_data_path("partial-axes.tsv"),
            mode="r",
        )
        fmt.validate(level="min")
        fmt.validate(level="max")

    def test_partial_axes_format_error_values(self):
        fmt = PartialAxesFormat(
            self.get_data_path("partial-axes-broken-values.tsv"),
            mode="r",
        )
        with self.assertRaisesRegex(ValidationError, "Line 3 has 3 columns"):
            fmt.validate()

    def test_group_summary_format_ok(self):
        fmt = GroupSummaryFormat(
            self.get_data_path("group-summary.tsv"),
            mode="r",
        )
        fmt.validate(level="min")
        fmt.validate(level="max")

    def test_group_summary_format_error_header(self):
        fmt = GroupSummaryFormat(
            self.get_data_path("group-summary-broken-header.tsv"),
            mode="r",
        )
        with self.assertRaisesRegex(ValidationError, "Invalid header"):
            fmt.validate()

    def test_mfa_results_directory_format_ok(self):
        fmt = MFAResultsDirFmt(self.get_data_path("mfa-results"), mode="r")
        fmt.validate(level="min")
        fmt.validate(level="max")
