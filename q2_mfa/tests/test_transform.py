# ----------------------------------------------------------------------------
# Copyright (c) 2026, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import unittest

import numpy as np
import pandas as pd
import pandas.testing as pdt
from numpy.testing import assert_allclose
from rachis import CategoricalMetadataColumn
from rachis.plugin.testing import TestPluginBase

from q2_mfa.transform import normalize_pqn, pretreat_metabolome, transform_clr


class TestTransformCLR(TestPluginBase):
    package = "q2_mfa.tests"

    def test_transform_clr_data_adaptive_uses_min_nonzero(self):
        df = pd.DataFrame(
            [[0, 1], [2, 3]],
        )

        exp = pd.DataFrame(
            [[-0.346574, 0.346574], [-0.143841, 0.143841]],
        )

        obs = transform_clr(df, pseudocount=None)
        pd.testing.assert_frame_equal(obs, exp)
        assert np.allclose(obs.sum(axis=1).to_numpy(), 0.0)

    def test_transform_clr_fixed_pseudocount(self):
        df = pd.DataFrame(
            [[0, 1], [2, 3]],
        )

        exp = pd.DataFrame(
            [[-0.549306, 0.549306], [-0.168236, 0.168236]],
        )

        obs = transform_clr(df, pseudocount=0.5)
        pd.testing.assert_frame_equal(obs, exp)
        assert np.allclose(obs.sum(axis=1).to_numpy(), 0.0)


class TestTransformLog(TestPluginBase):
    package = "q2_mfa.tests"

    def test_transform_log_data_adaptive_uses_min_nonzero(self):
        df = pd.DataFrame(
            [[0, 1], [2, 3]],
        )

        exp = pd.DataFrame(
            [[0.000000, 0.693147], [1.098612, 1.386294]],
        )

        obs = pretreat_metabolome(df, pseudocount=None, transform="log")
        pd.testing.assert_frame_equal(obs, exp)

    def test_transform_log_fixed_pseudocount(self):
        df = pd.DataFrame(
            [[0, 1], [2, 3]],
        )

        exp = pd.DataFrame(
            [[-0.693147, 0.405465], [0.916291, 1.252763]],
        )

        obs = pretreat_metabolome(df, pseudocount=0.5, transform="log")
        pd.testing.assert_frame_equal(obs, exp)


class TestPretreatMetabolome(TestPluginBase):
    package = "q2_mfa"

    def setUp(self):
        super().setUp()
        # All non-negative, includes zeros and positives (valid for log/sqrt)
        self.df_nonneg = pd.DataFrame(
            {
                "F1": [0.0, 1.0, 2.0],
                "F2": [3.0, 0.0, 4.0],
                "F3": [5.0, 6.0, 0.0],
            },
            index=["S1", "S2", "S3"],
        )

        # Contains a negative value (invalid for log/sqrt)
        self.df_has_negative = pd.DataFrame(
            {
                "F1": [0.0, -1.0, 2.0],
                "F2": [3.0, 0.0, 4.0],
                "F3": [5.0, 6.0, 0.0],
            },
            index=["S1", "S2", "S3"],
        )

        # No positive values anywhere -> pseudocount inference should fail for log
        self.df_no_positive = pd.DataFrame(
            {
                "F1": [0.0, 0.0, 0.0],
                "F2": [0.0, 0.0, 0.0],
                "F3": [0.0, 0.0, 0.0],
            },
            index=["S1", "S2", "S3"],
        )

        # Zero variance in at least one feature after centering decision:
        # Here F1 is constant; if center=False, autoscale/pareto should fail on sd==0.
        self.df_zero_variance_feature = pd.DataFrame(
            {
                "F1": [7.0, 7.0, 7.0],  # constant -> sd == 0
                "F2": [1.0, 2.0, 3.0],
                "F3": [2.0, 2.0, 5.0],
            },
            index=["S1", "S2", "S3"],
        )

        # Zero range in at least one feature when center=False:
        self.df_zero_range_feature = pd.DataFrame(
            {
                "F1": [9.0, 9.0, 9.0],  # max-min == 0
                "F2": [1.0, 2.0, 3.0],
                "F3": [4.0, 6.0, 8.0],
            },
            index=["S1", "S2", "S3"],
        )

        # Simple non-negative DF for deterministic golden tests
        self.df_small = pd.DataFrame(
            {
                "F1": [0.0, 1.0],
                "F2": [3.0, 7.0],
            },
            index=["S1", "S2"],
        )

        # A slightly larger DF for centering/scaling invariants
        self.df_nonneg = pd.DataFrame(
            {
                "F1": [0.0, 1.0, 2.0],
                "F2": [3.0, 0.0, 4.0],
                "F3": [5.0, 6.0, 0.0],
            },
            index=["S1", "S2", "S3"],
        )

        # DF suited to PQN: all positive, not identical across samples
        self.df_pqn = pd.DataFrame(
            {
                "F1": [10.0, 20.0, 30.0],
                "F2": [5.0, 10.0, 15.0],
                "F3": [2.0, 4.0, 6.0],
            },
            index=["S1", "S2", "S3"],
        )

    # --------- Value-based “golden” tests ---------

    def test_transform_log_with_fixed_pseudocount_exact(self):
        out = pretreat_metabolome(
            self.df_small,
            sample_normalization=None,
            transform="log",
            pseudocount=0.5,
            center=False,
            scale=None,
        )

        expected = np.log(self.df_small.to_numpy() + 0.5)
        assert_allclose(out.to_numpy(), expected, rtol=0, atol=1e-12)

    def test_transform_log_with_none_pseudocount(self):
        out = pretreat_metabolome(
            self.df_small,
            sample_normalization=None,
            transform="log",
            pseudocount=None,
            center=False,
            scale=None,
        )

        expected = np.log(self.df_small.to_numpy() + 1.0)
        assert_allclose(out.to_numpy(), expected, rtol=0, atol=1e-12)

    def test_transform_sqrt_exact(self):
        out = pretreat_metabolome(
            self.df_small,
            sample_normalization=None,
            transform="sqrt",
            center=False,
            scale=None,
        )

        expected = np.sqrt(self.df_small.to_numpy())
        assert_allclose(out.to_numpy(), expected, rtol=0, atol=1e-12)

    def test_centering_makes_feature_means_zero(self):
        out = pretreat_metabolome(
            self.df_nonneg,
            sample_normalization=None,
            transform=None,
            center=True,
            scale=None,
        )

        means = out.mean(axis=0).to_numpy()
        assert_allclose(means, np.zeros_like(means), rtol=0, atol=1e-12)

    def test_autoscale_only_no_centering_matches_definition(self):
        df = self.df_nonneg

        out = pretreat_metabolome(
            df,
            sample_normalization=None,
            transform=None,
            center=False,
            scale="autoscale",
        )

        # Expected manual computation
        X = df.astype(float)
        sd = X.std(axis=0, ddof=0)
        expected = X / sd

        assert_allclose(out.to_numpy(), expected.to_numpy(), atol=1e-12)

        # scaling should reduce std by exactly sd factor
        new_std = out.std(axis=0, ddof=0).to_numpy()
        original_std = X.std(axis=0, ddof=0).to_numpy()

        assert_allclose(new_std, original_std / original_std, atol=1e-12)

    def test_pareto_scaling(self):
        df = self.df_nonneg
        out = pretreat_metabolome(
            df,
            sample_normalization=None,
            transform=None,
            center=False,
            scale="pareto",
        )
        X = df.astype(float)
        sd = X.std(axis=0, ddof=0)
        expected = X / np.sqrt(sd)

        assert_allclose(out.to_numpy(), expected.to_numpy(), atol=1e-12)

    def test_range_scaling_only_no_centering_matches_definition(self):
        df = self.df_nonneg

        out = pretreat_metabolome(
            df,
            sample_normalization=None,
            transform=None,
            center=False,
            scale="range",
        )

        # Expected manual computation
        X = df.astype(float)
        rng = X.max(axis=0) - X.min(axis=0)
        expected = X / rng

        assert_allclose(out.to_numpy(), expected.to_numpy(), atol=1e-12)

        # resulting feature ranges should equal 1
        new_rng = out.max(axis=0) - out.min(axis=0)
        assert_allclose(new_rng.to_numpy(), np.ones_like(new_rng), atol=1e-12)

    # --------- PQN tests (don’t overfit; test properties) ---------

    def test_pqn_is_samplewise_scaling_only(self):
        # With PQN on, each sample should be scaled by a single factor
        # (ratios between features within a sample should be preserved)
        out = pretreat_metabolome(
            self.df_pqn,
            sample_normalization="pqn",
            pqn_method="median",
            transform=None,
            center=False,
            scale=None,
        )

        # For each sample i, out_i / in_i should be constant across features
        # (within numerical tolerance)
        ratio = out / self.df_pqn
        for sid in ratio.index:
            row = ratio.loc[sid].to_numpy()
            assert_allclose(row, np.full_like(row, row[0]), rtol=0, atol=1e-10)

    def test_pqn_does_not_change_zeros(self):
        df = self.df_nonneg.copy()
        out = pretreat_metabolome(
            df,
            sample_normalization="pqn",
        )
        # Multiplicative scaling should keep zeros as zeros
        mask = df.to_numpy() == 0.0
        self.assertTrue((out.to_numpy()[mask] == 0.0).all())

    # ---------- Happy-path tests ----------

    def test_preserves_shape_index_columns(self):
        out = pretreat_metabolome(
            self.df_nonneg,
            sample_normalization=None,
            transform="log",
            pseudocount=1e-6,
            center=True,
            scale=None,
        )
        self.assertIsInstance(out, pd.DataFrame)
        self.assertEqual(out.shape, self.df_nonneg.shape)
        self.assertListEqual(list(out.index), list(self.df_nonneg.index))
        self.assertListEqual(list(out.columns), list(self.df_nonneg.columns))

    # ---------- Error tests (assertRaisesRegex) ----------

    def test_log_raises_on_negative_values(self):
        with self.assertRaisesRegex(
            ValueError, r"Log transform requires non-negative values\."
        ):
            pretreat_metabolome(
                self.df_has_negative,
                transform="log",
                pseudocount=1e-6,
                center=False,
                scale=None,
            )

    def test_sqrt_raises_on_negative_values(self):
        with self.assertRaisesRegex(
            ValueError, r"Sqrt transform requires non-negative values\."
        ):
            pretreat_metabolome(
                self.df_has_negative,
                transform="sqrt",
                center=False,
                scale=None,
            )

    def test_log_infer_pseudocount_raises_when_no_positive_values(self):
        with self.assertRaisesRegex(
            ValueError,
            r"Cannot infer pseudocount: table has no positive "
            r"values\.\s*Provide `pseudocount` explicitly\.",
        ):
            pretreat_metabolome(
                self.df_no_positive,
                transform="log",
                pseudocount=None,
                center=False,
                scale=None,
            )

    def test_autoscale_raises_on_zero_variance_feature(self):
        with self.assertRaisesRegex(
            ValueError,
            r"Autoscaling not possible: at least one feature has zero variance\.",
        ):
            pretreat_metabolome(
                self.df_zero_variance_feature,
                transform=None,
                center=False,  # IMPORTANT: keep constant feature constant
                scale="autoscale",
            )

    def test_pareto_raises_on_zero_variance_feature(self):
        with self.assertRaisesRegex(
            ValueError,
            r"Pareto scaling not possible: at least one feature has zero variance\.",
        ):
            pretreat_metabolome(
                self.df_zero_variance_feature,
                transform=None,
                center=False,  # IMPORTANT
                scale="pareto",
            )

    def test_range_raises_on_zero_range_feature(self):
        with self.assertRaisesRegex(
            ValueError,
            r"Range scaling not possible: at least one feature has zero range\.",
        ):
            pretreat_metabolome(
                self.df_zero_range_feature,
                transform=None,
                center=False,  # IMPORTANT
                scale="range",
            )


class TestPQN(TestPluginBase):
    package = "q2_mfa"

    def setUp(self):
        super().setUp()
        self.df = pd.DataFrame(
            {
                "F1": [8.0, 4.0, 2.0],
                "F2": [16.0, 8.0, 3.0],
                "F3": [24.0, 12.0, 6.0],
            },
            index=["S1", "S2", "S3"],
        )

        self.df_negative = pd.DataFrame(
            {"F1": [1, -1], "F2": [2, 3]},
            index=["S1", "S2"],
        )

        self.df_all_zeros = pd.DataFrame(
            {"F1": [0, 0], "F2": [0, 0]},
            index=["S1", "S2"],
        )

        self.df_one_zero_sample = pd.DataFrame(
            {"F1": [0, 10, 10], "F2": [0, 20, 20]},
            index=["S0", "S1", "S2"],
        )

        self.ref_metadata = CategoricalMetadataColumn(
            pd.Series(
                {"S1": "control", "S2": "control", "S3": "treatment"},
                name="group",
            ).rename_axis("id")
        )

    def test_raises_on_negative_values(self):
        with self.assertRaisesRegex(ValueError, r"non-negative intensities"):
            normalize_pqn(self.df_negative, method="median")

    def test_raises_on_nan_factor_all_zeros(self):
        with self.assertRaisesRegex(ValueError, r"could not compute dilution factor"):
            normalize_pqn(self.df_all_zeros, method="median")

    def test_raises_on_non_positive_factor(self):
        with self.assertRaisesRegex(ValueError, r"non-positive dilution factor"):
            normalize_pqn(self.df_one_zero_sample, method="median")

    def test_pqn_median(self):
        out = normalize_pqn(self.df, method="median")

        exp = pd.DataFrame(
            {
                "F1": [4.0, 4.0, 4.0],
                "F2": [8.0, 8.0, 6.0],
                "F3": [12.0, 12.0, 12.0],
            },
            index=["S1", "S2", "S3"],
        )
        pdt.assert_frame_equal(out, exp)

    def test_pqn_mean(self):
        out = normalize_pqn(self.df, method="mean")

        exp = pd.DataFrame(
            {
                "F1": [14 / 3, 14 / 3, 14 / 3],
                "F2": [28 / 3, 28 / 3, 7.0],
                "F3": [14.0, 14.0, 14.0],
            },
            index=["S1", "S2", "S3"],
        )
        pdt.assert_frame_equal(out, exp)

    def test_pqn_metadata(self):
        out = normalize_pqn(
            self.df,
            method="median",
            ref_samples=self.ref_metadata,
            ref_label="control",
        )
        # Reference should be computed only from S1 and S2
        ref_expected = self.df.loc[["S1", "S2"]].median(axis=0)

        # Manually compute expected PQN normalization using the filtered reference
        ratios = self.df.div(ref_expected, axis=1)
        dilution_factors = ratios.median(axis=1)
        expected = self.df.div(dilution_factors, axis=0)

        pdt.assert_frame_equal(out, expected)

    def test_pqn_metadata_error(self):
        with self.assertRaisesRegex(
            ValueError, r"Reference label 'qc' not found in metadata column"
        ):
            normalize_pqn(
                self.df,
                method="median",
                ref_samples=self.ref_metadata,
                ref_label="qc",
            )


if __name__ == "__main__":
    unittest.main()
