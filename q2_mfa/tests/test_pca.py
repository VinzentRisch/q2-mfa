# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import numpy.testing as npt
import pandas as pd
import prince
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults

from q2_mfa.pca import pca


class TestPCA(TestPluginBase):
    package = "q2_mfa.tests"

    def setUp(self):
        super().setUp()
        self.table = pd.read_csv(
            self.get_data_path("random_data.txt"), sep="\t", index_col=0
        )

    def test_pca_parses_prince_values_and_names(self):
        ordn = pca(
            self.table,
            rescale_with_mean=True,
            rescale_with_std=False,
            n_components=2,
            n_iter=2,
            engine="scipy",
            random_state=None,
        )
        prince_result = prince.PCA(
            rescale_with_mean=True,
            rescale_with_std=False,
            n_components=2,
            n_iter=2,
            copy=True,
            check_input=True,
            random_state=None,
            engine="scipy",
        ).fit(self.table)

        prince_samples = prince_result.row_coordinates(self.table)
        prince_features = prince_result.column_coordinates_
        self.assertIsInstance(ordn, OrdinationResults)
        self.assertEqual(list(ordn.samples.index), list(self.table.index))
        self.assertEqual(list(ordn.features.index), list(self.table.columns))
        self.assertEqual(list(ordn.samples.columns), list(prince_samples.columns))
        self.assertEqual(list(ordn.features.columns), list(prince_features.columns))
        self.assertEqual(list(ordn.eigvals.index), [0, 1])
        self.assertEqual(list(ordn.proportion_explained.index), [0, 1])
        self.assertEqual(ordn.samples.shape, (self.table.shape[0], 2))
        self.assertEqual(ordn.features.shape, (self.table.shape[1], 2))
        self.assertEqual(len(ordn.eigvals), 2)
        self.assertEqual(len(ordn.proportion_explained), 2)

        npt.assert_allclose(ordn.samples.to_numpy(), prince_samples.to_numpy())
        npt.assert_allclose(ordn.features.to_numpy(), prince_features.to_numpy())
        npt.assert_allclose(ordn.eigvals.to_numpy(), prince_result.eigenvalues_)
        npt.assert_allclose(
            ordn.proportion_explained.to_numpy(),
            prince_result.percentage_of_variance_,
        )

    def test_pca_runs_with_generated_random_state(self):
        ordn = pca(
            self.table,
            n_components=2,
            random_state=None,
            engine="sklearn",
        )

        self.assertIsInstance(ordn, OrdinationResults)
        self.assertEqual(list(ordn.samples.index), list(self.table.index))
        self.assertEqual(list(ordn.features.index), list(self.table.columns))
        self.assertEqual(list(ordn.samples.columns), [0, 1])
        self.assertEqual(list(ordn.features.columns), [0, 1])
