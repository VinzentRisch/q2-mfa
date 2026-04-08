# ----------------------------------------------------------------------------
# Copyright (c) 2026, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd
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

    def test_shapes_and_labels(self):
        ordn = pca(self.table)

        self.assertIsInstance(ordn, OrdinationResults)

        # Indices preserved
        self.assertListEqual(list(ordn.samples.index), list(self.table.index))
        self.assertListEqual(list(ordn.features.index), list(self.table.columns))

        # Axis naming
        n_components_expected = min(self.table.shape[0], self.table.shape[1])
        expected_cols = [f"PC{i + 1}" for i in range(n_components_expected)]
        self.assertListEqual(list(ordn.samples.columns), expected_cols)
        self.assertListEqual(list(ordn.features.columns), expected_cols)
        self.assertListEqual(list(ordn.eigvals.index), expected_cols)
        self.assertListEqual(list(ordn.proportion_explained.index), expected_cols)

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
