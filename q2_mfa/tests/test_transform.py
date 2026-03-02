# ----------------------------------------------------------------------------
# Copyright (c) 2026, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import numpy as np
import pandas as pd
from rachis.plugin.testing import TestPluginBase

from q2_mfa.transform import transform_clr


class TestTransformCLR(TestPluginBase):
    package = "q2_mfa.tests"

    def setUp(self):
        super().setUp()

        self.df = pd.DataFrame(
            [[0, 1], [2, 3]],
        )

    def test_transform_clr_data_adaptive_uses_min_nonzero(self):
        # Apply pseudocount of 1 (minimum nonzero value)
        df_adjusted = self.df + 1
        # Calculate CLR: log(x) - mean(log(x))
        log_df = np.log(df_adjusted)
        exp = log_df.sub(log_df.mean(axis=1), axis=0)

        obs = transform_clr(self.df, pseudocount=None)
        pd.testing.assert_frame_equal(obs, exp)

    def test_transform_clr_fixed_pseudocount(self):
        # Apply pseudocount of 0.5
        df_adjusted = self.df + 0.5
        # Calculate CLR: log(x) - mean(log(x))
        log_df = np.log(df_adjusted)
        exp = log_df.sub(log_df.mean(axis=1), axis=0)

        obs = transform_clr(self.df, pseudocount=0.5)
        pd.testing.assert_frame_equal(obs, exp)
