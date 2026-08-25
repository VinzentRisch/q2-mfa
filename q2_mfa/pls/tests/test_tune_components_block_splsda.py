# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd
from pandas.testing import assert_frame_equal
from q2_types.feature_table import FeatureTable, Unconstrained
from rachis import Artifact, Metadata, ResultCollection, Visualization
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import PLSTuneComponentsDirFmt


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

    def _assert_tuning_matches_expected(self, tuning):
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

    def _tuning_parameters(self):
        return {
            "tables": self.tables,
            "y": self.response,
            "design_weight": 0.1,
            "ncomp": 2,
            "validation": "Mfold",
            "folds": 3,
            "nrepeat": 3,
            "seed": 1,
            "threads": 1,
        }

    def test_tune_components_action_matches_expected_values(self):
        tune_components = self.plugin.methods["_tune_components_block_splsda"]

        (tuning,) = tune_components(**self._tuning_parameters())

        self._assert_tuning_matches_expected(tuning)

    def test_tune_components_pipeline_matches_expected_values(self):
        tune_components = self.plugin.pipelines["tune_components_block_splsda"]

        result = tune_components(**self._tuning_parameters())

        self._assert_tuning_matches_expected(result.tuning)
        self.assertIsInstance(result.visualization, Visualization)
