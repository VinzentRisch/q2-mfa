# ----------------------------------------------------------------------------
# Copyright (c) 2026, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pca import pca


class TestMFA(TestPluginBase):
    package = "q2_mfa.tests"

    def setUp(self):
        super().setUp()
        self.table = pd.read_csv(
            self.get_data_path("random_data.txt"), sep="\t", index_col=0
        )

    def test_shapes_and_labels(self):
        ordn = pca(self.table)
        print(ordn)
