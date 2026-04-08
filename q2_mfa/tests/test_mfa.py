# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings

import pandas as pd
from rachis import Artifact
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults

from q2_mfa.mfa import mfa
from q2_mfa.pca import pca


class _FakeContext:
    def make_artifact(self, semantic_type, view, view_type=None):
        return Artifact.import_data(semantic_type, view, view_type=view_type)


class TestMFA(TestPluginBase):
    package = "q2_mfa.tests"

    def setUp(self):
        super().setUp()
        self.ctx = _FakeContext()

        self.table_a = pd.DataFrame(
            [[1.0, 3.0], [2.0, 5.0], [4.0, 6.0]],
            index=["sample-1", "sample-2", "sample-3"],
            columns=["feature-a1", "feature-a2"],
        )
        self.table_b = pd.DataFrame(
            [[10.0, 7.0], [8.0, 3.0], [6.0, 1.0]],
            index=["sample-3", "sample-1", "sample-2"],
            columns=["feature-b1", "feature-b2"],
        )
        self.artifact_a = Artifact.import_data("FeatureTable[Frequency]", self.table_a)
        self.artifact_b = Artifact.import_data("FeatureTable[Frequency]", self.table_b)

    def test_mfa_matches_classical_weighted_global_pca(self):
        obs_artifact = mfa(
            self.ctx,
            {
                "metabolome": self.artifact_a,
                "microbiome": self.artifact_b,
            },
        )
        obs = obs_artifact.view(OrdinationResults)

        self.assertIsInstance(obs, OrdinationResults)
        self.assertListEqual(list(obs.samples.index), list(self.table_a.index))
        self.assertListEqual(
            list(obs.features.index),
            [
                "metabolome:feature-a1",
                "metabolome:feature-a2",
                "microbiome:feature-b1",
                "microbiome:feature-b2",
            ],
        )

        reordered_b = self.table_b.loc[self.table_a.index]
        lambda_a = float(
            pca(self.table_a, n_components=1, svd_solver="full").eigvals.iloc[0]
        )
        lambda_b = float(
            pca(reordered_b, n_components=1, svd_solver="full").eigvals.iloc[0]
        )
        weighted = pd.concat(
            [
                self.table_a.div(lambda_a**0.5).rename(
                    columns=lambda c: f"metabolome:{c}"
                ),
                reordered_b.div(lambda_b**0.5).rename(
                    columns=lambda c: f"microbiome:{c}"
                ),
            ],
            axis=1,
        )
        exp = pca(weighted)

        self.assertEqual(obs.samples.shape, exp.samples.shape)
        self.assertEqual(obs.features.shape, exp.features.shape)
        pd.testing.assert_index_equal(obs.features.index, exp.features.index)
        pd.testing.assert_frame_equal(
            obs.samples.set_axis(exp.samples.columns, axis=1),
            exp.samples,
        )
        pd.testing.assert_frame_equal(
            obs.features.set_axis(exp.features.columns, axis=1),
            exp.features,
        )
        pd.testing.assert_series_equal(
            obs.eigvals.set_axis(exp.eigvals.index),
            exp.eigvals,
        )
        pd.testing.assert_series_equal(
            obs.proportion_explained.set_axis(exp.proportion_explained.index),
            exp.proportion_explained,
        )

    def test_mfa_drops_non_shared_samples_with_warning(self):
        mismatched = pd.DataFrame(
            [[1.0, 2.0], [3.0, 4.0], [8.0, 9.0]],
            index=["sample-1", "sample-3", "sample-x"],
            columns=["feature-c1", "feature-c2"],
        )

        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            obs_artifact = mfa(
                self.ctx,
                {
                    "metabolome": self.artifact_a,
                    "other": Artifact.import_data(
                        "FeatureTable[Frequency]", mismatched
                    ),
                },
            )
        obs = obs_artifact.view(OrdinationResults)

        self.assertEqual(len(observed), 2)
        self.assertIn("sample-2", str(observed[0].message))
        self.assertIn("sample-x", str(observed[1].message))
        self.assertListEqual(list(obs.samples.index), ["sample-1", "sample-3"])

    def test_mfa_requires_at_least_two_feature_tables(self):
        with self.assertRaisesRegex(ValueError, "at least two feature tables"):
            mfa(
                self.ctx,
                {
                    "metabolome": self.artifact_a,
                },
            )

    def test_mfa_raises_when_no_samples_are_shared(self):
        disjoint = pd.DataFrame(
            [[1.0, 2.0], [3.0, 4.0]],
            index=["sample-x", "sample-y"],
            columns=["feature-c1", "feature-c2"],
        )

        with self.assertRaisesRegex(ValueError, "do not share any sample IDs"):
            mfa(
                self.ctx,
                {
                    "metabolome": self.artifact_a,
                    "other": Artifact.import_data("FeatureTable[Frequency]", disjoint),
                },
            )

    def test_mfa_raises_when_first_eigenvalue_is_non_positive(self):
        constant = pd.DataFrame(
            [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]],
            index=["sample-1", "sample-2", "sample-3"],
            columns=["feature-c1", "feature-c2"],
        )

        with self.assertRaisesRegex(ValueError, "non-positive first eigenvalue"):
            mfa(
                self.ctx,
                {
                    "metabolome": Artifact.import_data(
                        "FeatureTable[Frequency]", constant
                    ),
                    "microbiome": self.artifact_b,
                },
            )

    def test_mfa_uses_user_parameters_for_global_pca_only(self):
        obs_artifact = mfa(
            self.ctx,
            {
                "metabolome": self.artifact_a,
                "microbiome": self.artifact_b,
            },
            n_components=1,
            svd_solver="full",
            random_state=0,
        )
        obs = obs_artifact.view(OrdinationResults)

        reordered_b = self.table_b.loc[self.table_a.index]
        lambda_a = float(
            pca(self.table_a, n_components=1, svd_solver="full").eigvals.iloc[0]
        )
        lambda_b = float(
            pca(reordered_b, n_components=1, svd_solver="full").eigvals.iloc[0]
        )
        weighted = pd.concat(
            [
                self.table_a.div(lambda_a**0.5).rename(
                    columns=lambda c: f"metabolome:{c}"
                ),
                reordered_b.div(lambda_b**0.5).rename(
                    columns=lambda c: f"microbiome:{c}"
                ),
            ],
            axis=1,
        )
        exp = pca(weighted, n_components=1, svd_solver="full", random_state=0)

        self.assertEqual(obs.samples.shape[1], 1)
        pd.testing.assert_frame_equal(
            obs.samples.set_axis(exp.samples.columns, axis=1),
            exp.samples,
        )
        pd.testing.assert_frame_equal(
            obs.features.set_axis(exp.features.columns, axis=1),
            exp.features,
        )
        pd.testing.assert_series_equal(
            obs.eigvals.set_axis(exp.eigvals.index),
            exp.eigvals,
        )
