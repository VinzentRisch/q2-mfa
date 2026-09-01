# -----------------------------------------------------------------------------
# Copyright (c) 2026, Rachis Developers.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

import json

import pandas as pd
from pandas.testing import assert_frame_equal
from q2_types.feature_table import FeatureTable, Unconstrained
from q2_types.tabular import TableJSONLFileFormat
from rachis import Artifact, Metadata, ResultCollection
from rachis.plugin.testing import TestPluginBase
from rpy2.robjects import r

from q2_mfa.pls import PLSFeatureSelectionDirFmt
from q2_mfa.pls.feature_selection_block_splsda import (
    _parse_keepx_collection,
    _r_feature_selection_error_rate_to_dataframe,
    _selected_features_table,
    _serialize_feature_selection,
)
from q2_mfa.pls.jsonl_descriptions import jsonl_descriptions


class TestFeatureSelectionBlockSPLSDA(TestPluginBase):
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
                name: Artifact.import_data(
                    FeatureTable[Unconstrained],
                    read_table(f"{name}.tsv"),
                )
                for name in ("block-a", "block-b")
            }
        )
        cls.response = Metadata(read_table("response.tsv")).get_column("group")

    def test_parse_keepx_collection_requires_expected_blocks(self):
        """Rejects keepX grids whose block names differ from the input blocks."""
        with self.assertRaisesRegex(ValueError, "must exactly match input block names"):
            _parse_keepx_collection({"block-a": "1,2"}, ("block-a", "block-b"))

    def test_parse_keepx_collection_parses_named_candidate_grids(self):
        """Converts each named comma-separated candidate grid to integers."""
        observed = _parse_keepx_collection(
            {
                "block-a": "1, 2, 3",
                "block-b": "4,5,6",
                "block-c": "7,8,9",
            },
            ("block-a", "block-b", "block-c"),
        )

        self.assertEqual(
            observed,
            {
                "block-a": [1, 2, 3],
                "block-b": [4, 5, 6],
                "block-c": [7, 8, 9],
            },
        )

    def test_parse_keepx_collection_requires_positive_integers(self):
        """Rejects non-positive and non-integer keepX candidate values."""
        for values in ("0,2", "one,2"):
            with self.subTest(values=values):
                with self.assertRaisesRegex(
                    ValueError,
                    "comma-separated list of positive integers",
                ):
                    _parse_keepx_collection(
                        {"block-a": values, "block-b": "1,2"},
                        ("block-a", "block-b"),
                    )

    def test_feature_selection_block_splsda_integration(self):
        """Runs the full action and selects one count from each two-value grid."""
        select_features = self.plugin.methods["_feature_selection_block_splsda"]

        (tuning,) = select_features(
            tables=self.tables,
            y=self.response,
            design_weight=0.1,
            ncomp=1,
            keepx={"block-a": "1,2", "block-b": "1,2"},
            validation="Mfold",
            folds=3,
            nrepeat=3,
            seed=1,
            threads=1,
        )

        tuning_data = tuning.view(PLSFeatureSelectionDirFmt)
        error_rates = tuning_data.error_rate.view(pd.DataFrame)
        selected_features = tuning_data.selected_features.view(pd.DataFrame)

        self.assertEqual(
            list(error_rates.columns),
            ["id", "component", "mean", "sd", "keepx_block-a", "keepx_block-b"],
        )
        self.assertTrue(error_rates["mean"].notna().all())
        self.assertTrue(error_rates["sd"].notna().all())
        self.assertEqual(set(error_rates["component"]), {0})
        self.assertEqual(len(error_rates), 4)
        self.assertEqual(set(error_rates["keepx_block-a"]), {1, 2})
        self.assertEqual(set(error_rates["keepx_block-b"]), {1, 2})
        self.assertEqual(selected_features["component"].tolist(), [0])
        self.assertEqual(
            selected_features.columns.tolist(), ["component", "block-a", "block-b"]
        )
        self.assertTrue(
            selected_features[["block-a", "block-b"]].isin([1, 2]).all().all()
        )

    def test_error_rate_table_converts_mixomics_statistics(self):
        """Converts the mixOmics mean and standard-deviation matrices to rows."""
        tune_result = r(
            "list("
            "error.rate = structure(matrix(c(0.2, 0.4), nrow = 2, "
            "dimnames = list(c('1_2', '3_4'), 'comp1'))), "
            "error.rate.sd = structure(matrix(c(0.01, 0.02), nrow = 2, "
            "dimnames = list(c('1_2', '3_4'), 'comp1'))))"
        )

        observed = _r_feature_selection_error_rate_to_dataframe(
            tune_result, ("block-a", "block-b")
        )
        expected = pd.DataFrame(
            {
                "component": [0, 0],
                "mean": [0.2, 0.4],
                "sd": [0.01, 0.02],
                "keepx_block-a": [1, 3],
                "keepx_block-b": [2, 4],
            },
        )

        assert_frame_equal(observed, expected)

    def test_selected_features_table_converts_mixomics_keepx(self):
        """Converts mixOmics selected keepX values to a feature table."""
        tune_result = r(
            "list(choice.keepX = list(" "metabolome = c(5, 7), microbiome = c(3, 4)))"
        )

        observed = _selected_features_table(tune_result)
        expected = pd.DataFrame(
            {"metabolome": [5, 7], "microbiome": [3, 4]},
            index=pd.Index([0, 1], name="component"),
        )

        assert_frame_equal(observed, expected)

    def test_serializer_writes_described_jsonl_files(self):
        """Writes both feature-selection outputs with their JSONL descriptions."""
        error_rates = pd.read_csv(
            self.get_data_path("feature-selection/serializer-error-rate.tsv"),
            sep="\t",
        )
        selected_features = pd.read_csv(
            self.get_data_path("feature-selection/serializer-selected-features.tsv"),
            sep="\t",
            index_col="component",
        )
        expected_error_rates = TableJSONLFileFormat(
            self.get_data_path(
                "feature-selection/serializer-expected-error-rate.jsonl"
            ),
            mode="r",
        ).view(pd.DataFrame)
        expected_selected_features = TableJSONLFileFormat(
            self.get_data_path(
                "feature-selection/serializer-expected-selected-features.jsonl"
            ),
            mode="r",
        ).view(pd.DataFrame)

        output = _serialize_feature_selection(error_rates, selected_features)
        error_rate_format = output.error_rate
        selected_features_format = output.selected_features

        for serialized, expected, description in (
            (
                error_rate_format,
                expected_error_rates,
                jsonl_descriptions["feature_selection_error_rate"],
            ),
            (
                selected_features_format,
                expected_selected_features,
                jsonl_descriptions["feature_selection_selected_features"],
            ),
        ):
            with serialized.path_maker().open() as fh:
                header = json.loads(next(fh))
            self.assertEqual(header["description"], description)
            assert_frame_equal(
                serialized.view(pd.DataFrame), expected, check_dtype=False
            )
