# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings

import numpy.testing as npt
import pandas as pd
import pandas.testing as pdt
import prince
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults

from q2_mfa.mfa import _build_prince_input, mfa
from q2_mfa.types import ComponentAnalysisDirFmt
from q2_mfa.types._transformer import _dataframe_to_numeric_tsv


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

    def _assert_prince_table_written(self, results, output, expected):
        observed = pd.read_csv(output.path_maker(), sep="\t")
        expected_format = _dataframe_to_numeric_tsv(expected)
        expected = pd.read_csv(str(expected_format), sep="\t")
        pdt.assert_frame_equal(observed, expected, check_dtype=False)

    def test_build_prince_input_success(self):
        tables = {"metabolome": self.table_a, "microbiome": self.table_b}
        table, groups = _build_prince_input(tables)

        self.assertEqual(len(table.index), 3)
        self.assertEqual(len(table.columns), 4)
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

    def test_mfa_parses_prince_values_and_names(self):
        tables = {"metabolome": self.table_a, "microbiome": self.table_b}
        results = mfa(tables=tables, engine="scipy")

        table, groups = _build_prince_input(tables)
        prince_result = prince.MFA(engine="scipy").fit(table, groups=groups)

        results.validate()
        ordn = results.ordination.view(OrdinationResults)
        prince_samples = prince_result.row_coordinates(table)
        prince_features = prince_result.column_coordinates_
        self.assertIsInstance(results, ComponentAnalysisDirFmt)
        self.assertIsInstance(ordn, OrdinationResults)

        npt.assert_allclose(ordn.samples.to_numpy(), prince_samples.to_numpy())
        npt.assert_allclose(ordn.features.to_numpy(), prince_features.to_numpy())
        npt.assert_allclose(ordn.eigvals.to_numpy(), prince_result.eigenvalues_)
        npt.assert_allclose(
            ordn.proportion_explained.to_numpy(),
            prince_result.percentage_of_variance_,
        )
        self._assert_prince_table_written(
            results,
            results.partial_sample_coordinates,
            prince_result.partial_row_coordinates(table),
        )
        self._assert_prince_table_written(
            results,
            results.sample_cosine_similarities,
            prince_result.row_cosine_similarities(table),
        )
        self._assert_prince_table_written(
            results,
            results.sample_contributions,
            prince_result.row_contributions_,
        )
        self._assert_prince_table_written(
            results,
            results.group_coordinates,
            prince_result.group_coordinates_,
        )
        self._assert_prince_table_written(
            results,
            results.group_contributions,
            prince_result.group_contributions_,
        )
        self._assert_prince_table_written(
            results,
            results.group_cosine_similarities,
            prince_result.group_cosine_similarities_,
        )
        self._assert_prince_table_written(
            results,
            results.partial_correlations,
            prince_result.partial_correlations_,
        )
        self._assert_prince_table_written(
            results,
            results.partial_contributions,
            prince_result.partial_contributions_,
        )
        self._assert_prince_table_written(
            results,
            results.feature_correlations,
            prince_result.column_correlations,
        )
        self._assert_prince_table_written(
            results,
            results.feature_contributions,
            prince_result.column_contributions_,
        )
        self._assert_prince_table_written(
            results,
            results.feature_cosine_similarities,
            prince_result.column_cosine_similarities_,
        )
