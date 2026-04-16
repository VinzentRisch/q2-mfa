# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings
from unittest.mock import MagicMock

import pandas as pd
from q2_types.ordination import OrdinationFormat, PCoAResults
from rachis import Artifact
from rachis.core.type import Properties
from rachis.plugin.testing import TestPluginBase

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

        cls.artifact_a = Artifact.import_data(
            "FeatureTable[Unconstrained]", cls.table_a
        )
        cls.artifact_b = Artifact.import_data(
            "FeatureTable[Unconstrained]", cls.table_b
        )
        cls.mismatched_artifact = Artifact.import_data(
            "FeatureTable[Unconstrained]", cls.mismatched
        )
        cls.disjoint_artifact = Artifact.import_data(
            "FeatureTable[Unconstrained]", cls.disjoint
        )
        cls.duplicate_a_artifact = Artifact.import_data(
            "FeatureTable[Unconstrained]", cls.duplicate_a
        )
        cls.duplicate_b_artifact = Artifact.import_data(
            "FeatureTable[Unconstrained]", cls.duplicate_b
        )
        cls.ordination_artifacts = {
            name: instance._load_ordination_artifact(name)
            for name in [
                "ord_group_a",
                "ord_group_b",
                "ord_global",
                "ord_group_other_shared",
                "ord_nonpositive",
            ]
        }

    def setUp(self):
        super().setUp()
        self.pca_action = MagicMock()
        self.ctx = MagicMock(
            get_action=MagicMock(return_value=self.pca_action),
            make_artifact=MagicMock(side_effect=self._make_artifact),
        )

    def _make_artifact(self, semantic_type, view, view_type=None):
        return Artifact.import_data(semantic_type, view, view_type=view_type)

    def _load_table(self, filename):
        return pd.read_csv(self.get_data_path(filename), sep="\t", index_col=0)

    def _load_ordination_artifact(self, prefix):
        return (
            Artifact.import_data(
                PCoAResults % Properties("pca"),
                self.get_data_path(f"mfa/{prefix}.ordination"),
                view_type=OrdinationFormat,
            ),
        )

    def _table_from_call(self, call_index):
        return (
            self.pca_action.call_args_list[call_index]
            .kwargs["table"]
            .view(pd.DataFrame)
        )

    def _assert_table_call_equal(self, call_index, expected):
        expected = expected.rename_axis(None)
        pd.testing.assert_frame_equal(self._table_from_call(call_index), expected)

    def _prefix_group_columns(self, table, group_name):
        prefixed = table.copy()
        prefixed.columns = [f"{group_name}:{feature}" for feature in prefixed.columns]
        return prefixed

    def test_mfa_orders_and_weights_tables(self):
        reordered_b = self.table_b.loc[self.table_a.index]
        expected_weighted = pd.concat(
            [
                self._prefix_group_columns(self.table_a.div(4.0**0.5), "metabolome"),
                self._prefix_group_columns(reordered_b.div(9.0**0.5), "microbiome"),
            ],
            axis=1,
        )
        self.pca_action.side_effect = [
            self.ordination_artifacts[name]
            for name in ["ord_group_a", "ord_group_b", "ord_global"]
        ]

        mfa(
            self.ctx,
            {"metabolome": self.artifact_a, "microbiome": self.artifact_b},
        )

        self.ctx.get_action.assert_called_once_with("mfa", "pca")
        self.assertEqual(self.pca_action.call_count, 3)
        self._assert_table_call_equal(0, self.table_a)
        self._assert_table_call_equal(1, reordered_b)
        self._assert_table_call_equal(2, expected_weighted)

    def test_mfa_drops_non_shared_samples_with_warning(self):
        shared_samples = pd.Index(["sample-1", "sample-3"])
        expected_weighted = pd.concat(
            [
                self._prefix_group_columns(
                    self.table_a.loc[shared_samples].div(4.0**0.5), "metabolome"
                ),
                self._prefix_group_columns(
                    self.mismatched.loc[shared_samples].div(16.0**0.5), "other"
                ),
            ],
            axis=1,
        )
        self.pca_action.side_effect = [
            self.ordination_artifacts[name]
            for name in ["ord_group_a", "ord_group_other_shared", "ord_global"]
        ]

        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            mfa(
                self.ctx,
                {"metabolome": self.artifact_a, "other": self.mismatched_artifact},
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
        self._assert_table_call_equal(0, self.table_a.loc[shared_samples])
        self._assert_table_call_equal(1, self.mismatched.loc[shared_samples])
        self._assert_table_call_equal(2, expected_weighted)

    def test_mfa_requires_at_least_two_feature_tables(self):
        with self.assertRaisesRegex(ValueError, "at least two feature tables"):
            mfa(self.ctx, {"metabolome": self.artifact_a})

        self.ctx.get_action.assert_called_once_with("mfa", "pca")
        self.pca_action.assert_not_called()

    def test_mfa_raises_when_no_samples_are_shared(self):
        with self.assertRaisesRegex(ValueError, "do not share any sample IDs"):
            mfa(
                self.ctx,
                {"metabolome": self.artifact_a, "other": self.disjoint_artifact},
            )

        self.ctx.get_action.assert_called_once_with("mfa", "pca")
        self.pca_action.assert_not_called()

    def test_mfa_raises_when_first_eigenvalue_is_non_positive(self):
        self.pca_action.side_effect = [self.ordination_artifacts["ord_nonpositive"]]

        with self.assertRaisesRegex(ValueError, "non-positive first eigenvalue"):
            mfa(
                self.ctx,
                {"metabolome": self.artifact_a, "microbiome": self.artifact_b},
            )

        self.ctx.get_action.assert_called_once_with("mfa", "pca")
        self.assertEqual(self.pca_action.call_count, 1)

    def test_mfa_prefixes_all_feature_names_with_group_name(self):
        self.pca_action.side_effect = [
            self.ordination_artifacts[name]
            for name in ["ord_group_a", "ord_group_b", "ord_global"]
        ]

        mfa(
            self.ctx,
            {
                "metabolome": self.duplicate_a_artifact,
                "microbiome": self.duplicate_b_artifact,
            },
        )

        expected_columns = [
            "metabolome:shared-feature",
            "metabolome:feature-a2",
            "microbiome:shared-feature",
            "microbiome:feature-b2",
        ]
        self.assertListEqual(list(self._table_from_call(2).columns), expected_columns)
        self.assertEqual(self.pca_action.call_count, 3)

    def test_mfa_returns_mfa_typed_artifact(self):
        self.pca_action.side_effect = [
            self.ordination_artifacts[name]
            for name in ["ord_group_a", "ord_group_b", "ord_global"]
        ]

        obs_artifact = mfa(
            self.ctx,
            {"metabolome": self.artifact_a, "microbiome": self.artifact_b},
        )

        self.assertEqual(str(obs_artifact.type), str(PCoAResults % Properties("mfa")))
