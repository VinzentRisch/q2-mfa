# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from unittest.mock import patch

import pandas as pd
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults

from q2_mfa.pca import pca


class TestPCA(TestPluginBase):
    package = "q2_mfa.tests"

    def setUp(self):
        super().setUp()
        self.table = pd.read_csv(
            self.get_data_path("pca/random_data.txt"), sep="\t", index_col=0
        )

    def test_pca_returns_expected_structure_for_two_components(self):
        ordn = pca(self.table, n_components=2)
        expected_columns = ["PC1", "PC2"]

        self.assertIsInstance(ordn, OrdinationResults)
        self.assertEqual(list(ordn.samples.index), list(self.table.index))
        self.assertEqual(list(ordn.features.index), list(self.table.columns))
        self.assertEqual(list(ordn.samples.columns), expected_columns)
        self.assertEqual(list(ordn.features.columns), expected_columns)
        self.assertEqual(list(ordn.eigvals.index), expected_columns)
        self.assertEqual(list(ordn.proportion_explained.index), expected_columns)
        self.assertEqual(ordn.samples.shape, (self.table.shape[0], 2))
        self.assertEqual(ordn.features.shape, (self.table.shape[1], 2))
        self.assertEqual(len(ordn.eigvals), 2)
        self.assertEqual(len(ordn.proportion_explained), 2)

    def test_pca_returns_all_components_when_n_components_is_none(self):
        ordn = pca(self.table, n_components=None)
        expected_count = min(self.table.shape)
        expected_columns = [f"PC{i + 1}" for i in range(expected_count)]

        self.assertIsInstance(ordn, OrdinationResults)
        self.assertEqual(list(ordn.samples.columns), expected_columns)
        self.assertEqual(list(ordn.features.columns), expected_columns)
        self.assertEqual(list(ordn.eigvals.index), expected_columns)
        self.assertEqual(list(ordn.proportion_explained.index), expected_columns)
        self.assertEqual(ordn.samples.shape, (self.table.shape[0], expected_count))
        self.assertEqual(ordn.features.shape, (self.table.shape[1], expected_count))
        self.assertEqual(len(ordn.eigvals), expected_count)
        self.assertEqual(len(ordn.proportion_explained), expected_count)

    def test_pca_accepts_random_state_with_randomized_solver(self):
        ordn = pca(
            self.table,
            n_components=2,
            svd_solver="randomized",
            random_state=42,
        )

        self.assertIsInstance(ordn, OrdinationResults)
        self.assertEqual(ordn.samples.shape, (self.table.shape[0], 2))
        self.assertEqual(ordn.features.shape, (self.table.shape[1], 2))
        self.assertEqual(list(ordn.samples.columns), ["PC1", "PC2"])

    @patch("q2_mfa.pca.secrets.randbits", return_value=123)
    def test_pca_generates_random_state_when_missing_for_randomized_solver(
        self, mock_randbits
    ):
        ordn = pca(
            self.table,
            n_components=2,
            svd_solver="randomized",
            random_state=None,
        )

        mock_randbits.assert_called_once_with(32)
        self.assertIsInstance(ordn, OrdinationResults)
        self.assertEqual(ordn.samples.shape, (self.table.shape[0], 2))
        self.assertEqual(ordn.features.shape, (self.table.shape[1], 2))
        self.assertEqual(list(ordn.samples.columns), ["PC1", "PC2"])
