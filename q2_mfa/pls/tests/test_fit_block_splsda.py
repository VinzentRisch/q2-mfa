# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
"""Tests the fitting action with current feature-selection artifacts."""

import pandas as pd
from q2_types.feature_table import FeatureTable, Unconstrained
from q2_types.tabular import TableJSONLFileFormat
from rachis import Artifact, Metadata
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import (
    AssociationMatrix,
    PLSComponentSelection,
    PLSFeatureSelection,
    PLSFeatureSelectionDirFmt,
    PLSFitDirFmt,
)
from q2_mfa.pls.descriptions import fit_descriptions
from q2_mfa.pls.examples import nutrimouse_tables_factory
from q2_mfa.pls.fit_block_splsda import (
    _block_wide_values,
    _feature_component_correlations,
    _feature_similarity_to_dataframe,
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
        cls.tables = {
            name: Artifact.import_data(
                FeatureTable[Unconstrained],
                pd.read_csv(
                    instance.get_data_path(f"tune-components/{name}.tsv"),
                    sep="\t",
                    index_col="id",
                ),
            )
            for name in ("block-a", "block-b")
        }
        cls.response = Metadata.load(
            instance.get_data_path("tune-components/response.tsv")
        ).get_column("group")
        cls.design = Artifact.import_data(
            AssociationMatrix,
            pd.read_csv(
                instance.get_data_path("utils/design-valid.tsv"),
                sep="\t",
                index_col="id",
            ),
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
                instance.get_data_path(f"fit/nutrimouse-{name}.tsv"),
                sep="\t",
                comment="#",
                dtype={"id": str, "sample": str},
            )
            for name in (
                "loadings",
                "variates",
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
        instance.package = "q2_mfa.pls.types.tests"
        cls.tuned = Artifact.import_data(
            PLSComponentSelection,
            instance.get_data_path("pls-tune-components"),
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

    def test_fit_uses_current_selection_artifacts(self):
        """Executes real R fitting using tuned components and wide keepX counts."""
        (result,) = self.plugin.methods["fit_block_splsda"](
            tables=self.tables,
            y=self.response,
            design_matrix=self.design,
            tuned_components=self.tuned,
            feature_selection=self.selection,
            folds=3,
            nrepeat=3,
            seed=1,
            threads=1,
        )
        fitted = result.view(PLSFitDirFmt)
        fitted.validate()
        loadings = fitted.loadings.view(pd.DataFrame)
        nonzero = loadings.loc[
            loadings["loading"].ne(0) & loadings["block"].isin(self.tables)
        ]
        counts = nonzero.groupby(["block", "component"]).size().to_dict()
        self.assertEqual(
            counts,
            {
                ("block-a", 1): 1,
                ("block-a", 2): 2,
                ("block-b", 1): 2,
                ("block-b", 2): 1,
            },
        )
        correlations = fitted.feature_component_correlation.view(pd.DataFrame)
        selected = set(zip(nonzero["block"], nonzero["feature"]))
        self.assertCountEqual(
            correlations[["block", "feature", "component"]].itertuples(
                index=False, name=None
            ),
            [(block, feature, comp) for block, feature in selected for comp in (1, 2)],
        )
        self.assertFalse(fitted.feature_similarity.view(pd.DataFrame).empty)
        stability = fitted.feature_stability.view(pd.DataFrame)
        self.assertEqual(
            stability.attrs["description"], fit_descriptions["feature_stability"]
        )
        frequencies = stability.set_index(["block", "feature", "component"])
        # b0 was selected in two folds of one repeat and omitted from the other two.
        self.assertAlmostEqual(
            frequencies.loc[("block-b", "b0", 2), "mean_selection_frequency"], 2 / 9
        )
        for error_file in (fitted.error_rate_weighted, fitted.error_rate_majority):
            self.assertEqual(set(error_file.view(pd.DataFrame)["component"]), {1, 2})

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
