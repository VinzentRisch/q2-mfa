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
from rpy2.robjects import r

from q2_mfa.pls import (
    AssociationMatrix,
    PLSComponentSelection,
    PLSFeatureSelection,
    PLSFeatureSelectionDirFmt,
    PLSFitDirFmt,
    utils,
)
from q2_mfa.pls.select_features_block_splsda import _serialize_feature_selection


class TestFitBlockSPLSDA(TestPluginBase):
    package = "q2_mfa.pls.tests"

    @classmethod
    def setUpClass(cls):
        """Loads shared tables and artifacts from existing fixtures."""
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
        instance.package = "q2_mfa.pls.types.tests"
        cls.tuned = Artifact.import_data(
            PLSComponentSelection,
            instance.get_data_path("pls-tune-components"),
        )

    def test_selected_counts_follow_requested_block_order(self):
        """Reads the wide selection table in fitting block order."""
        observed = utils._component_keepx_from_feature_selection(
            self.selection.view(PLSFeatureSelectionDirFmt),
            ["block-b", "block-a"],
            2,
        )
        self.assertEqual(observed, {"component-1": "2,1", "component-2": "1,2"})

    def test_selection_requires_matching_components(self):
        """Rejects selection counts that do not cover the fitted components."""
        with self.assertRaisesRegex(
            ValueError,
            "The feature-selection artifact must contain one keepX value for "
            "each input block and fitted component.",
        ):
            utils._component_keepx_from_feature_selection(
                self.selection.view(PLSFeatureSelectionDirFmt),
                ["block-a", "block-b"],
                3,
            )

    def test_fit_uses_current_selection_artifacts(self):
        """Executes real R fitting using tuned components and wide keepX counts."""
        r("pdf(file = NULL)")
        self.addCleanup(r["dev.off"])
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
        for error_file in (fitted.error_rate_weighted, fitted.error_rate_majority):
            self.assertEqual(set(error_file.view(pd.DataFrame)["component"]), {1, 2})
