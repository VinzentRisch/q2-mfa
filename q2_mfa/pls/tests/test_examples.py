# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import json

import pandas as pd
from pandas.testing import assert_frame_equal
from rachis import Metadata
from rachis.plugin.testing import TestPluginBase
from rachis.sdk.usage import ExecutionUsage

from q2_mfa.pls import PLSFeatureSelectionDirFmt


class TestUsageExamples(TestPluginBase):
    package = "q2_mfa.pls.tests"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        instance = cls()
        cls.expected_error_rates = pd.read_csv(
            instance.get_data_path("feature-selection/nutrimouse-error-rates.tsv"),
            sep="\t",
            index_col="id",
        )
        cls.expected_selected_features = pd.read_csv(
            instance.get_data_path(
                "feature-selection/nutrimouse-selected-features.tsv"
            ),
            sep="\t",
            index_col="id",
        )

    def test_feature_selection_block_splsda_nutrimouse(self):
        use = ExecutionUsage()
        action = self.plugin.pipelines["feature_selection_block_splsda"]
        action.examples["nutrimouse"](use)
        outputs = use.render()
        selection = outputs["feature_selection_nutrimouse"].execute()
        data = selection.view(PLSFeatureSelectionDirFmt)
        error_rates = data.error_rate.view(Metadata).to_dataframe()
        selected_features = data.selected_features.view(Metadata).to_dataframe()
        assert_frame_equal(
            error_rates,
            self.expected_error_rates,
            rtol=1e-8,
            atol=1e-10,
        )
        assert_frame_equal(selected_features, self.expected_selected_features)

        report = outputs["feature_selection_report"].execute()
        with (report._archiver.data_dir / "subfigures" / "index.json").open() as fh:
            report_index = json.load(fh)
        self.assertEqual(
            list(report_index),
            ["Error-rate heatmaps", "Error rates", "Selected features"],
        )
        self.assertEqual(
            list(report_index["Error-rate heatmaps"]["children"]),
            ["Component 1", "Component 2"],
        )
