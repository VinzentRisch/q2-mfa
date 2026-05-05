# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings

import numpy as np
import numpy.testing as npt
import pandas as pd
import prince
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults

from q2_mfa.mfa import mfa


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

    def _build_prince_input(self, feature_tables):
        consensus_samples = None
        for table in feature_tables.values():
            if consensus_samples is None:
                consensus_samples = table.index
            else:
                consensus_samples = consensus_samples.intersection(table.index)

        prefixed_tables = []
        groups = {}
        for group, table in feature_tables.items():
            table = table.loc[consensus_samples].copy()
            table.columns = [f"{group}:{feature}" for feature in table.columns]
            prefixed_tables.append(table)
            groups[group] = list(table.columns)

        table = pd.concat(prefixed_tables, axis=1)
        return table, groups

    def _read_ordination(self, results):
        return OrdinationResults.read(str(results.path / "ordination.txt"))

    def _read_table(self, results, filename):
        return pd.read_csv(results.path / filename, sep="\t")

    def _stringify_value_columns(self, table):
        table = table.copy()
        table.columns = [
            column if column == "id" else str(column) for column in table.columns
        ]
        table.columns.name = None
        return table

    def _assert_frame_values_equal(self, observed, expected):
        self.assertEqual(list(observed.index), list(expected.index))
        self.assertEqual(list(observed.columns), list(expected.columns))
        npt.assert_allclose(observed.to_numpy(), expected.to_numpy())

    def _prince_mfa(self, table, groups, **kwargs):
        return prince.MFA(
            rescale_with_mean=kwargs.get("rescale_with_mean", True),
            rescale_with_std=kwargs.get("rescale_with_std", True),
            n_components=kwargs.get("n_components", 2),
            n_iter=kwargs.get("n_iter", 3),
            copy=True,
            check_input=True,
            random_state=kwargs.get("random_state", None),
            engine=kwargs.get("engine", "scipy"),
        ).fit(table, groups=groups)

    def test_mfa_parses_prince_values_and_names(self):
        feature_tables = {
            "metabolome": self.table_a,
            "microbiome": self.table_b,
        }
        table, groups = self._build_prince_input(
            {"metabolome": self.table_a, "microbiome": self.table_b}
        )
        results = mfa(
            feature_tables,
            rescale_with_mean=True,
            rescale_with_std=True,
            n_components=2,
            n_iter=2,
            engine="scipy",
            random_state=None,
        )
        prince_result = self._prince_mfa(
            table,
            groups,
            n_components=2,
            n_iter=2,
            engine="scipy",
            random_state=None,
        )

        ordn = self._read_ordination(results)
        self.assertIsInstance(ordn, OrdinationResults)
        self.assertEqual(list(ordn.samples.index), list(table.index))
        self.assertEqual(list(ordn.features.index), list(table.columns))
        self.assertEqual(ordn.samples.shape, (table.shape[0], 2))
        self.assertEqual(ordn.features.shape, (table.shape[1], 2))
        self.assertEqual(len(ordn.eigvals), 2)
        self.assertEqual(len(ordn.proportion_explained), 2)

        npt.assert_allclose(
            ordn.samples.to_numpy(), prince_result.row_coordinates(table).to_numpy()
        )
        npt.assert_allclose(
            ordn.features.to_numpy(), prince_result.column_coordinates_.to_numpy()
        )
        npt.assert_allclose(ordn.eigvals.to_numpy(), prince_result.eigenvalues_)
        npt.assert_allclose(
            ordn.proportion_explained.to_numpy(),
            prince_result.percentage_of_variance_,
        )

        results.validate()

    def test_mfa_writes_prince_wide_outputs(self):
        feature_tables = {
            "metabolome": self.table_a,
            "microbiome": self.table_b,
        }
        table, groups = self._build_prince_input(
            {"metabolome": self.table_a, "microbiome": self.table_b}
        )
        results = mfa(
            feature_tables,
            n_components=2,
            engine="scipy",
            random_state=None,
        )
        prince_result = self._prince_mfa(table, groups, random_state=None)

        partial_coordinates = self._read_table(
            results, "partial-sample-coordinates.tsv"
        )
        expected_partial = prince_result.partial_row_coordinates(table).copy()
        expected_partial.columns = [
            f"{group}:{component}" for group, component in expected_partial.columns
        ]
        expected_partial.index.name = "id"
        expected_partial = expected_partial.reset_index()
        pd.testing.assert_frame_equal(partial_coordinates, expected_partial)

        sample_cos2 = self._read_table(results, "sample-cosine-similarities.tsv")
        expected_sample_cos2 = prince_result.row_cosine_similarities(table).copy()
        expected_sample_cos2.index.name = "id"
        expected_sample_cos2 = expected_sample_cos2.reset_index()
        expected_sample_cos2 = self._stringify_value_columns(expected_sample_cos2)
        pd.testing.assert_frame_equal(sample_cos2, expected_sample_cos2)

        feature_correlations = self._read_table(results, "feature-correlations.tsv")
        expected_correlations = prince_result.column_correlations.copy()
        expected_correlations.index.name = "id"
        expected_correlations = expected_correlations.reset_index()
        expected_correlations = self._stringify_value_columns(expected_correlations)
        pd.testing.assert_frame_equal(feature_correlations, expected_correlations)

        feature_contributions = self._read_table(results, "feature-contributions.tsv")
        expected_contributions = prince_result.column_contributions_.copy()
        expected_contributions.index.name = "id"
        expected_contributions = expected_contributions.reset_index()
        expected_contributions = self._stringify_value_columns(expected_contributions)
        pd.testing.assert_frame_equal(feature_contributions, expected_contributions)

        feature_cos2 = self._read_table(results, "feature-cosine-similarities.tsv")
        expected_feature_cos2 = prince_result.column_coordinates_.pow(2)
        expected_feature_cos2 = expected_feature_cos2.divide(
            expected_feature_cos2.sum(axis=1).replace(0, np.nan), axis=0
        ).fillna(0.0)
        expected_feature_cos2.index.name = "id"
        expected_feature_cos2 = expected_feature_cos2.reset_index()
        expected_feature_cos2 = self._stringify_value_columns(expected_feature_cos2)
        pd.testing.assert_frame_equal(feature_cos2, expected_feature_cos2)

    def test_mfa_writes_derived_outputs(self):
        feature_tables = {
            "metabolome": self.table_a,
            "microbiome": self.table_b,
        }
        table, groups = self._build_prince_input(
            {"metabolome": self.table_a, "microbiome": self.table_b}
        )
        results = mfa(
            feature_tables,
            n_components=2,
            engine="scipy",
            random_state=None,
        )
        prince_result = self._prince_mfa(table, groups, random_state=None)

        partial_axes = self._read_table(results, "partial-axes.tsv")
        expected_partial_axes = []
        global_scores = prince_result.row_coordinates(table)
        for group, columns in groups.items():
            group_scores = prince_result[group].row_coordinates(table.loc[:, columns])
            for partial_component in group_scores.columns:
                for global_component in global_scores.columns:
                    expected_partial_axes.append(
                        {
                            "group": group,
                            "partial_component": partial_component,
                            "global_component": global_component,
                            "correlation": float(
                                group_scores[partial_component].corr(
                                    global_scores[global_component]
                                )
                            ),
                        }
                    )
        expected_partial_axes = pd.DataFrame(expected_partial_axes)
        pd.testing.assert_frame_equal(partial_axes, expected_partial_axes)

        group_summary = self._read_table(results, "group-summary.tsv")
        expected_group_summary = []
        eigenvalues = pd.Series(prince_result.eigenvalues_)
        for group, columns in groups.items():
            group_contribution = prince_result.column_contributions_.loc[columns].sum(
                axis=0
            )
            first_eigenvalue = float(prince_result[group].eigenvalues_[0])
            group_dist2 = float(
                np.square(prince_result[group].eigenvalues_ / first_eigenvalue).sum()
            )
            for component in group_contribution.index:
                contribution = float(group_contribution[component])
                coordinate = float(contribution * eigenvalues[component])
                expected_group_summary.append(
                    {
                        "group": group,
                        "component": component,
                        "coordinate": coordinate,
                        "contribution": contribution,
                        "cos2": float((coordinate**2) / group_dist2),
                    }
                )
        expected_group_summary = pd.DataFrame(expected_group_summary)
        pd.testing.assert_frame_equal(group_summary, expected_group_summary)

    def test_mfa_drops_non_shared_samples_with_warning(self):
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            results = mfa(
                {"metabolome": self.table_a, "other": self.mismatched},
                n_components=2,
                engine="scipy",
                random_state=None,
            )

        self.assertEqual(len(observed), 2)
        self.assertEqual(
            str(observed[0].message),
            (
                "\n\033[93mDropping samples from group 'metabolome' that are not "
                "shared across all tables:\nsample-2\033[0m"
            ),
        )
        self.assertEqual(
            str(observed[1].message),
            (
                "\n\033[93mDropping samples from group 'other' that are not "
                "shared across all tables:\nsample-x\033[0m"
            ),
        )
        ordn = self._read_ordination(results)
        self.assertEqual(list(ordn.samples.index), ["sample-1", "sample-3"])

    def test_mfa_requires_at_least_two_feature_tables(self):
        with self.assertRaisesRegex(ValueError, "at least two feature tables"):
            mfa({"metabolome": self.table_a})

    def test_mfa_raises_when_no_samples_are_shared(self):
        with self.assertRaisesRegex(ValueError, "do not share any sample IDs"):
            mfa({"metabolome": self.table_a, "other": self.disjoint})

    def test_mfa_prefixes_all_feature_names_with_group_name(self):
        results = mfa(
            {
                "metabolome": self.duplicate_a,
                "microbiome": self.duplicate_b,
            },
            n_components=2,
            engine="scipy",
            random_state=None,
        )

        ordn = self._read_ordination(results)
        expected_features = [
            "metabolome:shared-feature",
            "metabolome:feature-a2",
            "microbiome:shared-feature",
            "microbiome:feature-b2",
        ]
        self.assertListEqual(list(ordn.features.index), expected_features)

    def test_mfa_runs_with_generated_random_state(self):
        results = mfa(
            {"metabolome": self.table_a, "microbiome": self.table_b},
            n_components=2,
            random_state=None,
            engine="sklearn",
        )

        ordn = self._read_ordination(results)
        self.assertIsInstance(ordn, OrdinationResults)
        self.assertEqual(ordn.samples.shape[1], 2)
        self.assertEqual(ordn.features.shape[1], 2)
