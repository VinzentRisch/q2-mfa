# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import numpy.testing as npt
import pandas as pd
import pandas.testing as pdt
import prince
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults

from q2_mfa.pca import pca
from q2_mfa.types import ComponentAnalysisDirFmt


class TestPCA(TestPluginBase):
    package = "q2_mfa.tests"

    def setUp(self):
        super().setUp()
        self.table = pd.read_csv(
            self.get_data_path("pca/random_data.txt"), sep="\t", index_col=0
        )

    def _assert_prince_table_written(self, results, output, expected):
        observed = pd.read_csv(output.path_maker(), sep="\t")
        expected = expected.rename_axis("id").reset_index()
        expected.columns = expected.columns.astype(str)
        expected.columns.name = None
        pdt.assert_frame_equal(observed, expected, check_dtype=False)

    def test_pca_parses_prince_values_and_names(self):
        results = pca(
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

        results.validate()
        ordn = results.ordination.view(OrdinationResults)
        prince_samples = prince_result.row_coordinates(self.table)
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
            results.sample_cosine_similarities,
            prince_result.row_cosine_similarities(self.table),
        )
        self._assert_prince_table_written(
            results,
            results.sample_contributions,
            prince_result.row_contributions_,
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

    def test_pca_runs_with_generated_random_state(self):
        results = pca(
            self.table,
            n_components=2,
            random_state=None,
            engine="sklearn",
        )

        ordn = results.ordination.view(OrdinationResults)

        self.assertIsInstance(ordn, OrdinationResults)
        self.assertEqual(list(ordn.samples.index), list(self.table.index))
        self.assertEqual(list(ordn.features.index), list(self.table.columns))
        self.assertEqual(list(ordn.samples.columns), [0, 1])
        self.assertEqual(list(ordn.features.columns), [0, 1])
