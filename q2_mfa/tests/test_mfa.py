# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings
from unittest.mock import Mock, patch

import numpy.testing as npt
import pandas as pd
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults

from q2_mfa.mfa import (
    _as_prince_wide_table,
    _build_prince_input,
    _create_mfa_results,
    _to_ordination,
    mfa,
)
from q2_mfa.types import ComponentAnalysisDirFmt


class TestMFA(TestPluginBase):
    package = "q2_mfa.tests"

    @classmethod
    def setUpClass(cls):
        instance = cls()
        cls.table_a = instance._load_table("mfa/mfa_table_a.tsv")
        cls.table_b = instance._load_table("mfa/mfa_table_b.tsv")
        cls.mismatched = instance._load_table("mfa/mfa_mismatched.tsv")
        cls.disjoint = instance._load_table("mfa/mfa_disjoint.tsv")
        cls.duplicate_a = instance._load_table("mfa/mfa_duplicate_a.tsv")
        cls.duplicate_b = instance._load_table("mfa/mfa_duplicate_b.tsv")

    def _load_table(self, filename):
        return pd.read_csv(self.get_data_path(filename), sep="\t", index_col=0)

    def test_build_prince_input_success(self):
        feature_tables = {"metabolome": self.table_a, "microbiome": self.table_b}
        table, groups = _build_prince_input(feature_tables)

        self.assertEqual(len(table.index), 3)  # common samples
        self.assertEqual(len(table.columns), 4)  # 2+2 features
        self.assertIn("metabolome:feature-a1", table.columns)
        self.assertIn("microbiome:feature-b1", table.columns)
        self.assertEqual(
            groups["metabolome"], ["metabolome:feature-a1", "metabolome:feature-a2"]
        )

    def test_build_prince_input_drops_samples_with_warning(self):
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            table, _ = _build_prince_input(
                {"metabolome": self.table_a, "other": self.mismatched}
            )

        self.assertEqual(len(observed), 2)
        self.assertIn(
            "Dropping samples from group 'metabolome'", str(observed[0].message)
        )
        self.assertIn("Dropping samples from group 'other'", str(observed[1].message))
        self.assertEqual(list(table.index), ["sample-1", "sample-3"])

    def test_build_prince_input_error_fewer_than_two_tables(self):
        with self.assertRaisesRegex(ValueError, "at least two feature tables"):
            _build_prince_input({"metabolome": self.table_a})

    def test_build_prince_input_error_illegal_group_name(self):
        with self.assertRaisesRegex(ValueError, "cannot contain ':'"):
            _build_prince_input({"illegal:name": self.table_a, "other": self.table_b})

    def test_build_prince_input_error_no_shared_samples(self):
        with self.assertRaisesRegex(ValueError, "do not share any sample IDs"):
            _build_prince_input({"metabolome": self.table_a, "other": self.disjoint})

    def test_as_prince_wide_table_multiindex_rows(self):
        df = pd.DataFrame(
            {"val": [1, 2]},
            index=pd.MultiIndex.from_tuples(
                [("A", "x"), ("B", "y")], names=["L1", "L2"]
            ),
        )
        result = _as_prince_wide_table(df)
        self.assertEqual(list(result["id"]), ["A:x", "B:y"])

    def test_as_prince_wide_table_multiindex_columns(self):
        df = pd.DataFrame(
            [[1, 2]],
            index=["s1"],
            columns=pd.MultiIndex.from_tuples(
                [("A", "x"), ("B", "y")], names=["L1", "L2"]
            ),
        )
        result = _as_prince_wide_table(df)
        self.assertEqual(list(result.columns), ["id", "A:x", "B:y"])
        self.assertEqual(result["id"].iloc[0], "s1")

    def test_to_ordination(self):
        mock_mfa = Mock()
        mock_mfa.eigenvalues_ = [0.5, 0.3]
        mock_mfa.percentage_of_variance_ = [0.6, 0.4]
        expected_samples = pd.DataFrame({"comp1": [1, 2]}, index=["s1", "s2"])
        mock_mfa.row_coordinates.return_value = expected_samples
        expected_features = pd.DataFrame({"comp1": [0.1, 0.2]}, index=["f1", "f2"])
        mock_mfa.column_coordinates_ = expected_features

        table = pd.DataFrame()
        ordn = _to_ordination(mock_mfa, table)

        self.assertIsInstance(ordn, OrdinationResults)
        npt.assert_array_equal(ordn.eigvals, [0.5, 0.3])
        npt.assert_array_equal(ordn.proportion_explained, [0.6, 0.4])
        pd.testing.assert_frame_equal(ordn.samples, expected_samples)
        pd.testing.assert_frame_equal(ordn.features, expected_features)

    def test_create_mfa_results(self):
        ordn = OrdinationResults(
            "MFA", "MFA", pd.Series([1, 2]), pd.DataFrame({"0": [1]}, index=["s1"])
        )
        tables = {"test-table.tsv": pd.DataFrame({"col": [1]}, index=["s1"])}

        results = _create_mfa_results(ordn, tables)

        self.assertIsInstance(results, ComponentAnalysisDirFmt)
        self.assertTrue((results.path / "test-table.tsv").exists())
        self.assertTrue((results.path / "ordination.txt").exists())

    def test_mfa_integration(self):
        feature_tables = {"metabolome": self.table_a, "microbiome": self.table_b}
        results = mfa(
            feature_tables,
            n_components=2,
            engine="scipy",
            random_state=None,
        )

        self.assertIsInstance(results, ComponentAnalysisDirFmt)
        results.validate()

        ordn = OrdinationResults.read(str(results.path / "ordination.txt"))
        self.assertEqual(len(ordn.samples), 3)
        self.assertEqual(len(ordn.features), 4)

    @patch("q2_mfa.mfa._create_mfa_results")
    @patch("q2_mfa.mfa._to_ordination")
    @patch("q2_mfa.mfa._build_prince_input")
    @patch("q2_mfa.mfa.prince.MFA")
    @patch("q2_mfa.mfa.secrets.randbits", return_value=12345)
    def test_mfa_runs_with_generated_random_state(
        self,
        randbits,
        prince_mfa,
        build_prince_input,
        to_ordination,
        create_mfa_results,
    ):
        table = pd.DataFrame({"feature": [1.0]}, index=["sample"])
        build_prince_input.return_value = (table, {"group": ["feature"]})
        prince_mfa.return_value.fit.return_value = Mock()

        mfa(
            {"metabolome": self.table_a, "microbiome": self.table_b},
            n_components=2,
            random_state=None,
            engine="sklearn",
        )

        randbits.assert_called_once_with(32)
        self.assertEqual(prince_mfa.call_args.kwargs["random_state"], 12345)
        create_mfa_results.assert_called_once()
