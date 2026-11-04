# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
"""Tests the fitting action with current feature-selection artifacts."""

import pandas as pd
from q2_types.tabular import TableJSONLFileFormat
from rachis import Artifact
from rachis.plugin.testing import TestPluginBase
from rpy2.robjects import r

from q2_mfa.pls import PLSFeatureSelection, PLSFeatureSelectionDirFmt, PLSFitDirFmt
from q2_mfa.pls.examples import nutrimouse_tables_factory
from q2_mfa.pls.fit_block_splsda import (
    _block_wide_values,
    _consensus_variates,
    _feature_component_correlations,
    _feature_similarity_to_dataframe,
    _r_auc_to_dataframe,
    _r_ave_to_dataframe,
    _r_criterion_to_dataframe,
    _r_feature_stability_to_dataframe,
    _resolve_fit_keepx,
    _write_fit_table,
)
from q2_mfa.pls.select_features_block_splsda import _serialize_feature_selection


class TestFitBlockSPLSDA(TestPluginBase):
    package = "q2_mfa.pls.tests"

    @classmethod
    def setUpClass(cls):
        """Loads shared artifacts and mixOmics reference results."""
        super().setUpClass()
        instance = cls()
        cls.ave_values = r["source"](instance.get_data_path("fit/ave-input.R")).rx2(
            "value"
        )
        cls.ave_expected = pd.read_csv(
            instance.get_data_path("fit/ave-expected.tsv"), sep="\t"
        )
        cls.criterion_values = r["source"](
            instance.get_data_path("fit/criterion-input.R")
        ).rx2("value")
        cls.criterion_expected = pd.read_csv(
            instance.get_data_path("fit/criterion-expected.tsv"), sep="\t"
        )
        cls.auc_values = r["source"](instance.get_data_path("fit/auc-input.R")).rx2(
            "value"
        )
        cls.auc_expected = pd.read_csv(
            instance.get_data_path("fit/auc-expected.tsv"), sep="\t"
        )
        cls.feature_stability_values = r["source"](
            instance.get_data_path("fit/feature-stability-input.R")
        ).rx2("value")
        cls.feature_stability_expected = pd.read_csv(
            instance.get_data_path("fit/feature-stability-expected.tsv"), sep="\t"
        )
        error_rates = (
            TableJSONLFileFormat(
                instance.get_data_path(
                    "feature-selection/serializer-expected-error-rate.jsonl"
                ),
                mode="r",
            )
            .view(pd.DataFrame)
            .drop(columns="id")
        )
        selected = (
            TableJSONLFileFormat(
                instance.get_data_path(
                    "feature-selection/serializer-expected-selected-features.jsonl"
                ),
                mode="r",
            )
            .view(pd.DataFrame)
            .drop(columns="id")
            .set_index("component")
        )
        cls.selection = Artifact.import_data(
            PLSFeatureSelection, _serialize_feature_selection(error_rates, selected)
        )
        cls.nutrimouse_expected = {
            name: pd.read_csv(
                instance.get_data_path(f"fit/nutrimouse/{name}.tsv"),
                sep="\t",
                comment="#",
                dtype={"id": str, "sample": str},
            )
            for name in (
                "loadings",
                "variates",
                "weights",
                "consensus-variates",
                "feature-component-correlation",
                "feature-similarity",
                "feature-similarity-comp1",
            )
        }
        cls.nutrimouse_matrices = {}
        for name, identifier, value in (
            ("loadings", "feature", "loading"),
            ("variates", "sample", "score"),
            ("feature-component-correlation", "feature", "correlation"),
        ):
            cls.nutrimouse_matrices[name] = {
                block: table.pivot_table(
                    index=identifier, columns="component", values=value, sort=False
                )
                for block, table in cls.nutrimouse_expected[name].groupby(
                    "block", sort=False
                )
            }
        cls.nutrimouse_tables = nutrimouse_tables_factory()
        cls.nutrimouse_weights = cls.nutrimouse_expected["weights"].pivot(
            index="block", columns="component", values="weight"
        )

    def test_r_ave_to_dataframe(self):
        """Preserves block and overall AVE metrics with one-based components."""
        pd.testing.assert_frame_equal(
            _r_ave_to_dataframe(self.ave_values), self.ave_expected
        )

    def test_r_criterion_to_dataframe(self):
        """Numbers components and restarts iterations for each convergence trace."""
        pd.testing.assert_frame_equal(
            _r_criterion_to_dataframe(self.criterion_values), self.criterion_expected
        )

    def test_r_auc_to_dataframe(self):
        """Flattens R AUC matrices while preserving labels and values."""
        pd.testing.assert_frame_equal(
            _r_auc_to_dataframe(self.auc_values), self.auc_expected
        )

    def test_r_feature_stability_to_dataframe(self):
        """Averages frequencies across repeats, including omitted features as zero."""
        pd.testing.assert_frame_equal(
            _r_feature_stability_to_dataframe(self.feature_stability_values),
            self.feature_stability_expected,
        )

    def test_selected_counts_follow_requested_block_order(self):
        """Reads the wide selection table in fitting block order."""
        observed = _resolve_fit_keepx(
            None,
            self.selection.view(PLSFeatureSelectionDirFmt),
            ["block-b", "block-a"],
            2,
        )
        self.assertEqual(
            list(observed.items()), [("block-b", [2, 1]), ("block-a", [1, 2])]
        )

    def test_selection_requires_matching_components(self):
        """Rejects selection counts that do not cover the fitted components."""
        with self.assertRaisesRegex(
            ValueError,
            "The feature-selection artifact must contain one row per fitted "
            "component.",
        ):
            _resolve_fit_keepx(
                None,
                self.selection.view(PLSFeatureSelectionDirFmt),
                ["block-a", "block-b"],
                3,
            )

    def test_feature_component_correlations_match_plot_var(self):
        """Matches the labelled component correlations returned by plotVar."""
        correlations = _feature_component_correlations(
            {
                block: table.view(pd.DataFrame)
                for block, table in self.nutrimouse_tables.items()
            },
            self.nutrimouse_matrices["variates"],
            self.nutrimouse_matrices["loadings"],
        )
        fitted = PLSFitDirFmt()
        _write_fit_table(
            fitted.feature_component_correlation,
            _block_wide_values(correlations, "feature", "correlation"),
            "feature_component_correlation",
        )
        pd.testing.assert_frame_equal(
            fitted.feature_component_correlation.view(pd.DataFrame),
            self.nutrimouse_expected["feature-component-correlation"],
            check_dtype=False,
        )

    def test_consensus_variates_match_plot_indiv(self):
        """Matches mixOmics averages with aligned sample and component labels."""
        variates = dict(self.nutrimouse_matrices["variates"])
        variates["lipid"] = variates["lipid"].iloc[::-1, ::-1]
        consensus = _consensus_variates(variates, self.nutrimouse_weights.iloc[:, ::-1])
        fitted = PLSFitDirFmt()
        _write_fit_table(
            fitted.consensus_variates,
            _block_wide_values(consensus, "sample", "score").rename(
                columns={"block": "method"}
            ),
            "consensus_variates",
        )
        pd.testing.assert_frame_equal(
            fitted.consensus_variates.view(pd.DataFrame),
            self.nutrimouse_expected["consensus-variates"],
            check_dtype=False,
        )

    def test_feature_similarity_matches_circos_plot(self):
        """Matches circosPlot similarities using saved plotVar correlations."""
        correlations = self.nutrimouse_matrices["feature-component-correlation"]
        for component_count, key in (
            (1, "feature-similarity-comp1"),
            (2, "feature-similarity"),
        ):
            with self.subTest(components=component_count):
                expected = self.nutrimouse_expected[key]
                selected = set(expected["feature_1"]) | set(expected["feature_2"])
                observed = _feature_similarity_to_dataframe(
                    {
                        block: table.loc[
                            table.index.isin(selected),
                            table.columns[:component_count],
                        ]
                        for block, table in correlations.items()
                    }
                )
                fitted = PLSFitDirFmt()
                _write_fit_table(
                    fitted.feature_similarity, observed, "feature_similarity"
                )
                pd.testing.assert_frame_equal(
                    fitted.feature_similarity.view(pd.DataFrame),
                    expected,
                    check_dtype=False,
                )
