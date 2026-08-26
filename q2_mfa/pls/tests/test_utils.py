# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings
from unittest.mock import Mock, patch

import pandas as pd
from rachis import Metadata
from rachis.core.exceptions import RachisWarning
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import utils


class TestPLSUtils(TestPluginBase):
    package = "q2_mfa.pls.tests"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        instance = cls()

        def read_table(name):
            return pd.read_csv(
                instance.get_data_path(f"utils/{name}"), sep="\t", index_col="id"
            )

        cls.blocks = {
            "block-a": read_table("block-a.tsv"),
            "block-b": read_table("block-b.tsv"),
        }
        cls.response = Metadata(read_table("response.tsv")).get_column("group")
        cls.designs = {
            name: Metadata(read_table(f"design-{name}.tsv"))
            for name in ("valid", "nonnumeric", "nonsymmetric", "nonzero-diagonal")
        }

    def test_align_samples_drops_unshared_and_unlabelled_samples(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            blocks, target = utils._align_samples(
                self.blocks, self.response.to_series()
            )

        self.assertEqual([warning.category for warning in caught], [RachisWarning] * 3)
        self.assertEqual(
            [str(warning.message) for warning in caught],
            [
                "Dropping samples from block 'block-a' that are not shared "
                "across all blocks:\ns1, s6",
                "Dropping samples from block 'block-b' that are not shared "
                "across all blocks:\ns4, s6",
                "Dropping samples from block 'y' that are not shared across all "
                "blocks:\ns5",
            ],
        )
        self.assertEqual(list(blocks), ["block-a", "block-b"])
        for table in blocks.values():
            self.assertEqual(table.index.tolist(), ["s2", "s3"])
        self.assertEqual(target.index.tolist(), ["s2", "s3"])

    def test_align_samples_rejects_fewer_than_two_tables(self):
        with self.assertRaisesRegex(
            ValueError, "At least two named feature tables are required."
        ):
            utils._align_samples(
                {"block-a": self.blocks["block-a"]}, self.response.to_series()
            )

    def test_align_samples_rejects_inputs_without_shared_samples(self):
        blocks = {
            "block-a": self.blocks["block-a"].rename(
                index=lambda sample: f"a-{sample}"
            ),
            "block-b": self.blocks["block-b"].rename(
                index=lambda sample: f"b-{sample}"
            ),
        }
        with self.assertRaisesRegex(
            ValueError, "The input feature tables and response share no sample IDs."
        ):
            utils._align_samples(blocks, self.response.to_series())

    def test_resolve_design_rejects_missing_design_options(self):
        with self.assertRaisesRegex(
            ValueError, "Provide exactly one of 'design-matrix' or 'design-weight'."
        ):
            utils._resolve_design(None, None, list(self.blocks))

    def test_resolve_design_rejects_both_design_options(self):
        with self.assertRaisesRegex(
            ValueError, "Provide exactly one of 'design-matrix' or 'design-weight'."
        ):
            utils._resolve_design(self.designs["valid"], 0.1, list(self.blocks))

    def test_resolve_design_returns_scalar_weight(self):
        self.assertEqual(utils._resolve_design(None, 0.1, list(self.blocks)), 0.1)

    def test_resolve_design_rejects_mismatched_block_names(self):
        invalid = (
            self.designs["valid"].to_dataframe().rename(index={"block-a": "other"})
        )
        with self.assertRaisesRegex(
            ValueError,
            "The row and column names in 'design-matrix' must exactly match ",
        ):
            utils._resolve_design(Metadata(invalid), None, list(self.blocks))

    def test_resolve_design_rejects_non_numeric_values(self):
        with self.assertRaisesRegex(
            ValueError, "Values in 'design-matrix' must be numeric."
        ):
            utils._resolve_design(self.designs["nonnumeric"], None, list(self.blocks))

    def test_resolve_design_rejects_non_symmetric_matrix(self):
        with self.assertRaisesRegex(ValueError, "'design-matrix' must be symmetrical."):
            utils._resolve_design(self.designs["nonsymmetric"], None, list(self.blocks))

    def test_resolve_design_rejects_nonzero_diagonal(self):
        with self.assertRaisesRegex(
            ValueError, "The diagonal of 'design-matrix' must contain only zeroes."
        ):
            utils._resolve_design(
                self.designs["nonzero-diagonal"], None, list(self.blocks)
            )

    def test_resolve_design_reorders_valid_matrix_to_block_order(self):
        observed = utils._resolve_design(self.designs["valid"], None, list(self.blocks))
        expected = pd.DataFrame(
            [[0.0, 0.2], [0.2, 0.0]],
            index=pd.Index(["block-a", "block-b"], name="id"),
            columns=["block-a", "block-b"],
        )
        pd.testing.assert_frame_equal(observed, expected)

    def test_build_bpparam_uses_serial_backend_for_one_thread(self):
        r = Mock()
        r.__getitem__ = Mock(return_value=Mock())
        with patch.object(utils, "r", r):
            utils._build_bpparam(1, 4)
        r.__getitem__.assert_called_once_with("SerialParam")
        r.__getitem__.return_value.assert_called_once_with(RNGseed=4)

    def test_build_bpparam_uses_multicore_workers(self):
        r = Mock()
        r.__getitem__ = Mock(return_value=Mock())
        with patch.object(utils, "r", r), patch.object(
            utils.platform, "system", return_value="Darwin"
        ):
            utils._build_bpparam(3, 4)
        r.__getitem__.assert_called_once_with("MulticoreParam")
        r.__getitem__.return_value.assert_called_once_with(RNGseed=4, workers=3)

    def test_build_bpparam_uses_snow_backend_on_windows(self):
        r = Mock()
        r.__getitem__ = Mock(return_value=Mock())
        with patch.object(utils, "r", r), patch.object(
            utils.platform, "system", return_value="Windows"
        ):
            utils._build_bpparam(2, 4)
        r.__getitem__.assert_called_once_with("SnowParam")
        r.__getitem__.return_value.assert_called_once_with(
            type="SOCK", RNGseed=4, workers=2
        )

    def test_build_bpparam_delegates_worker_count_for_zero_threads(self):
        r = Mock()
        r.__getitem__ = Mock(return_value=Mock())
        with patch.object(utils, "r", r), patch.object(
            utils.platform, "system", return_value="Darwin"
        ):
            utils._build_bpparam(0, 4)
        r.__getitem__.assert_called_once_with("MulticoreParam")
        r.__getitem__.return_value.assert_called_once_with(RNGseed=4)

    def test_to_r_inputs_preserves_block_and_sample_labels(self):
        sample_ids = ["s2", "s3"]
        blocks = {name: table.loc[sample_ids] for name, table in self.blocks.items()}
        target = self.response.to_series().loc[sample_ids]

        r_blocks, r_target, r_design = utils._to_r_inputs(
            blocks, target, self.designs["valid"].to_dataframe()
        )

        self.assertEqual(list(r_blocks.names), ["block-a", "block-b"])
        self.assertEqual(list(utils.r["rownames"](r_blocks.rx2("block-a"))), sample_ids)
        self.assertEqual(list(r_target.names), sample_ids)
        self.assertEqual(list(utils.r["as.character"](r_target)), ["case", "control"])
        self.assertEqual(list(utils.r["rownames"](r_design)), ["block-b", "block-a"])
        self.assertEqual(list(utils.r["colnames"](r_design)), ["block-b", "block-a"])

    def test_vote_error_rates_combines_mean_and_standard_deviation(self):
        perf_result = utils.r("""
            list(
              `WeightedVote.error.rate` = list(
                `max.dist` = matrix(
                  c(0.1, 0.2, 0.3, 0.4), nrow = 2, byrow = TRUE,
                  dimnames = list(c("Overall.BER", "Overall.ER"), c("comp1", "comp2"))
                )
              ),
              `WeightedVote.error.rate.sd` = list(
                `max.dist` = matrix(
                  c(0.01, 0.02, 0.03, 0.04), nrow = 2, byrow = TRUE,
                  dimnames = list(c("Overall.BER", "Overall.ER"), c("comp1", "comp2"))
                )
              )
            )
            """)
        observed = utils._r_vote_error_rate_to_dataframe(perf_result, "WeightedVote")

        expected = pd.DataFrame(
            {
                "distance": ["max.dist"] * 4,
                "class": ["Overall.BER", "Overall.BER", "Overall.ER", "Overall.ER"],
                "component": [0, 1, 0, 1],
                "mean": [0.1, 0.2, 0.3, 0.4],
                "sd": [0.01, 0.02, 0.03, 0.04],
            }
        )
        pd.testing.assert_frame_equal(observed, expected)

    def test_vote_error_rates_omits_missing_standard_deviation(self):
        perf_result = utils.r("""
            list(
              `WeightedVote.error.rate` = list(
                `max.dist` = matrix(
                  c(0.1, 0.3), nrow = 2,
                  dimnames = list(c("Overall.BER", "Overall.ER"), "comp1")
                )
              ),
              `WeightedVote.error.rate.sd` = NULL
            )
            """)
        observed = utils._r_vote_error_rate_to_dataframe(perf_result, "WeightedVote")

        self.assertEqual(observed["mean"].tolist(), [0.1, 0.3])
        self.assertTrue(observed["sd"].isna().all())

    def test_vote_error_rates_returns_empty_table_when_both_statistics_are_missing(
        self,
    ):
        perf_result = utils.r("""
            list(
              `WeightedVote.error.rate` = NULL,
              `WeightedVote.error.rate.sd` = NULL
            )
            """)
        observed = utils._r_vote_error_rate_to_dataframe(perf_result, "WeightedVote")
        self.assertTrue(observed.empty)
        self.assertEqual(
            observed.columns.tolist(), ["distance", "class", "component", "mean", "sd"]
        )
