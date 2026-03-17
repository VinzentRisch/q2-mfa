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
from skbio.stats.composition import clr, multi_replace

from q2_mfa.transform import transform_clr


class TestTransformCLR(TestPluginBase):
    package = "q2_mfa.tests"

    def setUp(self):
        super().setUp()

        self.df = pd.DataFrame(
            [[0, 1], [2, 3]],
            index=["sample-1", "sample-2"],
            columns=["feature-1", "feature-2"],
        )

    def test_transform_clr_data_adaptive_uses_min_nonzero(self):
        df_adjusted = self.df + 1
        log_df = np.log(df_adjusted)
        exp = log_df.sub(log_df.mean(axis=1), axis=0)

        obs = transform_clr(
            self.df,
            pseudocount=None,
            replacement_method="pseudocount",
        )
        pd.testing.assert_frame_equal(obs, exp)

    def test_transform_clr_fixed_pseudocount(self):
        df_adjusted = self.df + 0.5
        log_df = np.log(df_adjusted)
        exp = log_df.sub(log_df.mean(axis=1), axis=0)

        obs = transform_clr(
            self.df,
            pseudocount=0.5,
            replacement_method="pseudocount",
        )
        pd.testing.assert_frame_equal(obs, exp)

    def test_transform_clr_multiplicative_fixed_delta(self):
        replaced = multi_replace(self.df, delta=0.5)
        exp = pd.DataFrame(
            clr(replaced),
            index=self.df.index,
            columns=self.df.columns,
        )

        obs = transform_clr(
            self.df,
            delta=0.5,
        )
        pd.testing.assert_frame_equal(obs, exp)

    def test_multiplicative_all_zero_sample_raises(self):
        df = pd.DataFrame(
            [[0, 0], [2, 3]],
            index=["sample-1", "sample-2"],
            columns=["feature-1", "feature-2"],
        )

        with self.assertRaisesRegex(ValueError, "all 0"):
            transform_clr(df)

    def test_pseudocount_all_zero_table_raises(self):
        df = pd.DataFrame(
            [[0, 0], [0, 0]],
            index=["sample-1", "sample-2"],
            columns=["feature-1", "feature-2"],
        )

        with self.assertRaisesRegex(ValueError, "infer a pseudocount"):
            transform_clr(df, replacement_method="pseudocount")

    def test_transform_clr_sparse_data(self):
        # Create sparse random data with 90% zeros
        np.random.seed(42)
        data = np.random.randint(0, 1001, size=(100, 50))
        zero_mask = np.random.choice([True, False], size=data.shape, p=[0.9, 0.1])
        zero_mask[:, 0] = False
        data[zero_mask] = 0
        df_sparse = pd.DataFrame(
            data,
            index=[f"sample-{i}" for i in range(100)],
            columns=[f"feature-{j}" for j in range(50)],
        )

        obs = transform_clr(df_sparse)

        self.assertTrue(np.isfinite(obs.to_numpy()).all())
        np.testing.assert_allclose(obs.sum(axis=1).to_numpy(), 0.0, atol=1e-10)
