# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd
from rachis.core.exceptions import ValidationError
from rachis.plugin.testing import TestPluginBase

import q2_mfa.plugin_setup  # noqa: F401
from q2_mfa.types import ComponentAnalysisDirFmt, NumericTSVFormat


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
        fmt = ComponentAnalysisDirFmt(self.get_data_path("mfa-results"), mode="r")
        fmt.validate()

    def test_pca_results_directory_format_ok(self):
        fmt = ComponentAnalysisDirFmt(self.get_data_path("pca-results"), mode="r")
        fmt.validate()

    def test_dataframe_to_numeric_tsv_flattens_multiindex_rows(self):
        df = pd.DataFrame(
            {"val": [1, 2]},
            index=pd.MultiIndex.from_tuples(
                [("A", "x"), ("B", "y")], names=["L1", "L2"]
            ),
        )
        transformer = self.get_transformer(pd.DataFrame, NumericTSVFormat)
        fmt = transformer(df)

        result = pd.read_csv(str(fmt), sep="\t", index_col="id")

        self.assertEqual(list(result.index), ["A:x", "B:y"])

    def test_dataframe_to_numeric_tsv_flattens_multiindex_columns(self):
        df = pd.DataFrame(
            [[1, 2]],
            index=["s1"],
            columns=pd.MultiIndex.from_tuples(
                [("A", "x"), ("B", "y")], names=["L1", "L2"]
            ),
        )
        transformer = self.get_transformer(pd.DataFrame, NumericTSVFormat)
        fmt = transformer(df)

        result = pd.read_csv(str(fmt), sep="\t", index_col="id")

        self.assertEqual(list(result.columns), ["A:x", "B:y"])
        self.assertEqual(list(result.index), ["s1"])

    def test_dataframe_to_numeric_tsv_writes_flat_table(self):
        df = pd.DataFrame(
            {"0": [1, 2], "1": [3, 4]},
            index=["s1", "s2"],
        )

        transformer = self.get_transformer(pd.DataFrame, NumericTSVFormat)
        fmt = transformer(df)
        result = pd.read_csv(str(fmt), sep="\t", index_col="id")

        self.assertEqual(list(result.columns), ["0", "1"])
        self.assertEqual(list(result.index), ["s1", "s2"])
        self.assertEqual(list(result["0"]), [1, 2])
        self.assertEqual(list(result["1"]), [3, 4])
