# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults
from sklearn.decomposition import PCA as SklearnPCA

from q2_mfa.pca import pca


class TestPCA(TestPluginBase):
    package = "q2_mfa.tests"

    def setUp(self):
        super().setUp()
        self.table = pd.read_csv(
            self.get_data_path("random_data.txt"), sep="\t", index_col=0
        )

    def test_pca_matches_sklearn_outputs(self):
        ordn = pca(self.table, n_components=2, svd_solver="full")

        self.assertIsInstance(ordn, OrdinationResults)

        sklearn_pca = SklearnPCA(
            n_components=2,
            svd_solver="full",
        )
        transformed = sklearn_pca.fit_transform(self.table)
        expected_cols = ["PC1", "PC2"]

        expected_samples = pd.DataFrame(
            transformed,
            index=self.table.index,
            columns=expected_cols,
        )
        expected_features = pd.DataFrame(
            sklearn_pca.components_.T,
            index=self.table.columns,
            columns=expected_cols,
        )
        expected_eigvals = pd.Series(
            sklearn_pca.explained_variance_,
            index=expected_cols,
        )
        expected_proportion_explained = pd.Series(
            sklearn_pca.explained_variance_ratio_,
            index=expected_cols,
        )

        pd.testing.assert_frame_equal(ordn.samples, expected_samples)
        pd.testing.assert_frame_equal(ordn.features, expected_features)
        pd.testing.assert_series_equal(ordn.eigvals, expected_eigvals)
        pd.testing.assert_series_equal(
            ordn.proportion_explained, expected_proportion_explained
        )

    def test_invalid_parameter_combination_raises_value_error(self):
        with self.assertRaisesRegex(
            ValueError,
            r"Wrong PCA parameter combination: .*with svd_solver='randomized'",
        ):
            pca(
                self.table,
                n_components="mle",
                svd_solver="randomized",
            )
