# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from unittest.mock import MagicMock, call, patch

import pandas as pd
from pandas.testing import assert_frame_equal
from q2_types.feature_table import FeatureTable, Unconstrained
from rachis import Artifact, Metadata, ResultCollection
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import PLSTuneComponentsDirFmt
from q2_mfa.pls.tune_components_block_splsda import tune_components_block_splsda


class TestTuneComponentsBlockSPLSDA(TestPluginBase):
    package = "q2_mfa.pls.tests"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        instance = cls()

        def read_table(name):
            return pd.read_csv(
                instance.get_data_path(f"tune-components/{name}"),
                sep="\t",
                index_col="id",
            )

        cls.tables = ResultCollection(
            {
                "block-a": Artifact.import_data(
                    FeatureTable[Unconstrained], read_table("block-a.tsv")
                ),
                "block-b": Artifact.import_data(
                    FeatureTable[Unconstrained], read_table("block-b.tsv")
                ),
            }
        )
        cls.response = Metadata(read_table("response.tsv")).get_column("group")
        cls.expected_weighted_error_rates = read_table("weighted-error-rates.tsv")
        cls.expected_majority_error_rates = read_table("majority-error-rates.tsv")
        cls.expected_weighted_choices = read_table("weighted-choices.tsv")
        cls.expected_majority_choices = read_table("majority-choices.tsv")

    def test_tune_components_action_matches_expected_values(self):
        tune_components = self.plugin.methods["_tune_components_block_splsda"]

        (tuning,) = tune_components(
            tables=self.tables,
            y=self.response,
            design_weight=0.1,
            ncomp=2,
            validation="Mfold",
            folds=3,
            nrepeat=3,
            seed=1,
            threads=1,
        )

        tuning_data = tuning.view(PLSTuneComponentsDirFmt)
        actual_tables = (
            (
                tuning_data.error_rate_weighted.view(Metadata).to_dataframe(),
                self.expected_weighted_error_rates,
                True,
            ),
            (
                tuning_data.error_rate_majority.view(Metadata).to_dataframe(),
                self.expected_majority_error_rates,
                True,
            ),
            (
                tuning_data.choice_matrix_weighted.view(Metadata).to_dataframe(),
                self.expected_weighted_choices,
                False,
            ),
            (
                tuning_data.choice_matrix_majority.view(Metadata).to_dataframe(),
                self.expected_majority_choices,
                False,
            ),
        )

        for actual, expected, has_error_rates in actual_tables:
            if has_error_rates:
                assert_frame_equal(actual, expected, rtol=1e-8, atol=1e-10)
            else:
                assert_frame_equal(actual, expected, check_exact=True)

    @patch("q2_mfa.pls.tune_components_block_splsda._error_rate_metadata")
    def test_tune_components_pipeline_calls_its_actions(self, mock_error_rate_metadata):
        tuning = MagicMock()
        mock_action = MagicMock(
            side_effect=[
                lambda *args, **kwargs: (tuning,),
                lambda *args, **kwargs: (MagicMock(),),
                lambda *args, **kwargs: (MagicMock(),),
            ]
        )
        mock_context = MagicMock(get_action=mock_action)

        tune_components_block_splsda(
            ctx=mock_context,
            tables=self.tables,
            y=self.response,
            design_weight=0.1,
        )

        self.assertEqual(
            mock_context.get_action.call_args_list,
            [
                call("mfa", "_tune_components_block_splsda"),
                call("vizard", "lineplot"),
                call("metadata", "tabulate"),
            ],
        )
