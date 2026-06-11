# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings

import numpy.testing as npt
import pandas as pd
import pandas.testing as pdt
import prince
from rachis import Metadata
from rachis.plugin.testing import TestPluginBase
from skbio import OrdinationResults

from q2_mfa.mfa import (
    _build_prince_input,
    _metadata_to_grouped_tables,
    _parse_metadata_groups,
    _validate_group_name,
    mfa,
)
from q2_mfa.types import ComponentAnalysisDirFmt
from q2_mfa.types._transformer import _dataframe_to_numeric_tsv


class TestMFA(TestPluginBase):
    package = "q2_mfa.tests"

    @classmethod
    def setUpClass(cls):
        instance = cls()
        cls.table_a = instance._load_table("mfa/mfa_table_a.tsv")
        cls.table_b = instance._load_table("mfa/mfa_table_b.tsv")
        cls.mismatched = instance._load_table("mfa/mfa_mismatched.tsv")
        cls.disjoint = instance._load_table("mfa/mfa_disjoint.tsv")
        cls.duplicate_a = instance._load_table("mfa/mfa_duplicate_a.tsv")
        cls.duplicate_b = instance._load_table("mfa/mfa_duplicate_b.tsv")
        cls.filter_table_a = instance._load_table("mfa/mfa_filter_table_a.tsv")
        cls.filter_table_b = instance._load_table("mfa/mfa_filter_table_b.tsv")
        cls.filter_drop_group = instance._load_table("mfa/mfa_filter_drop_group.tsv")
        cls.sample_metadata = Metadata.load(
            instance.get_data_path("mfa/mfa_metadata.tsv")
        )

    def _load_table(self, filename):
        return pd.read_csv(self.get_data_path(filename), sep="\t", index_col=0)

    def _assert_prince_table_written(self, results, output, expected):
        observed = pd.read_csv(output.path_maker(), sep="\t")
        expected_format = _dataframe_to_numeric_tsv(expected)
        expected = pd.read_csv(str(expected_format), sep="\t")
        pdt.assert_frame_equal(observed, expected, check_dtype=False)

    def test_validate_group_name(self):
        self.assertIsNone(_validate_group_name("clinical"))

    def test_validate_group_name_error(self):
        with self.assertRaisesRegex(ValueError, "cannot contain ':'"):
            _validate_group_name("clinical:metadata")

    def test_parse_metadata_groups_default(self):
        observed = _parse_metadata_groups(None, ["age", "bmi"])

        self.assertEqual(observed, {"metadata": ["age", "bmi"]})

    def test_parse_metadata_groups_string_group_name(self):
        observed = _parse_metadata_groups("clinical", ["age", "bmi"])

        self.assertEqual(observed, {"clinical": ["age", "bmi"]})

    def test_parse_metadata_groups_error_empty_string(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            _parse_metadata_groups(" ", ["age", "bmi"])

    def test_parse_metadata_groups_mapping_string_columns(self):
        observed = _parse_metadata_groups(
            {"clinical": "age, bmi", "body": "score"},
            ["age", "bmi", "score"],
        )

        self.assertEqual(observed, {"clinical": ["age", "bmi"], "body": ["score"]})

    def test_parse_metadata_groups_error_empty_group_name(self):
        with self.assertRaisesRegex(ValueError, "names cannot be empty"):
            _parse_metadata_groups({"": "age"}, ["age", "bmi"])

    def test_parse_metadata_groups_error_empty_columns(self):
        with self.assertRaisesRegex(ValueError, "must contain at least one column"):
            _parse_metadata_groups({"clinical": " , "}, ["age", "bmi"])

    def test_metadata_to_grouped_tables_none(self):
        self.assertEqual(_metadata_to_grouped_tables(None, None), {})

    def test_metadata_to_grouped_tables_error_groups_without_metadata(self):
        with self.assertRaisesRegex(ValueError, "requires sample_metadata"):
            _metadata_to_grouped_tables(None, {"clinical": "age"})

    def test_metadata_to_grouped_tables_selects_groups(self):
        observed = _metadata_to_grouped_tables(
            self.sample_metadata,
            {"clinical": "age,score", "body": "bmi"},
        )

        self.assertEqual(list(observed), ["clinical", "body"])
        pdt.assert_frame_equal(
            observed["clinical"],
            self.sample_metadata.to_dataframe().loc[:, ["age", "score"]],
        )
        pdt.assert_frame_equal(
            observed["body"],
            self.sample_metadata.to_dataframe().loc[:, ["bmi"]],
        )

    def test_metadata_to_grouped_tables_error_unknown_column(self):
        with self.assertRaisesRegex(ValueError, "not present in the metadata: nope"):
            _metadata_to_grouped_tables(self.sample_metadata, {"clinical": "nope"})

    def test_metadata_to_grouped_tables_error_duplicate_column(self):
        with self.assertRaisesRegex(
            ValueError, "cannot be assigned to multiple groups: age"
        ):
            _metadata_to_grouped_tables(
                self.sample_metadata,
                {"clinical": "age", "body": "age"},
            )

    def test_build_prince_input_tables(self):
        tables = {"metabolome": self.table_a, "microbiome": self.table_b}
        table, groups = _build_prince_input(tables)

        self.assertEqual(list(table.index), ["sample-1", "sample-2", "sample-3"])
        self.assertEqual(
            list(table.columns),
            [
                "metabolome:feature-a1",
                "metabolome:feature-a2",
                "microbiome:feature-b1",
                "microbiome:feature-b2",
            ],
        )
        self.assertEqual(
            groups,
            {
                "metabolome": [
                    "metabolome:feature-a1",
                    "metabolome:feature-a2",
                ],
                "microbiome": [
                    "microbiome:feature-b1",
                    "microbiome:feature-b2",
                ],
            },
        )

    def test_build_prince_input_tables_metadata(self):
        tables = {"metabolome": self.table_a}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            table, groups = _build_prince_input(
                tables,
                self.sample_metadata,
                {"clinical": "age", "body": "bmi"},
            )

        self.assertEqual(list(table.index), ["sample-1", "sample-2", "sample-3"])
        self.assertEqual(
            list(table.columns),
            [
                "metabolome:feature-a1",
                "metabolome:feature-a2",
                "clinical:age",
                "body:bmi",
            ],
        )
        self.assertEqual(
            groups,
            {
                "metabolome": [
                    "metabolome:feature-a1",
                    "metabolome:feature-a2",
                ],
                "clinical": ["clinical:age"],
                "body": ["body:bmi"],
            },
        )

    def test_build_prince_input_metadata(self):
        table, groups = _build_prince_input(
            sample_metadata=self.sample_metadata,
            metadata_groups={"clinical": "age", "body": "bmi"},
        )

        self.assertEqual(
            list(table.index),
            ["sample-1", "sample-2", "sample-3", "sample-4"],
        )
        self.assertEqual(list(table.columns), ["clinical:age", "body:bmi"])
        self.assertEqual(
            groups,
            {
                "clinical": ["clinical:age"],
                "body": ["body:bmi"],
            },
        )

    def test_build_prince_input_drops_samples_with_warning(self):
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            table, _ = _build_prince_input(
                {"metabolome": self.table_a, "other": self.mismatched}
            )

        self.assertEqual(len(observed), 2)
        self.assertIn(
            "Dropping samples from group 'metabolome'", str(observed[0].message)
        )
        self.assertIn("Dropping samples from group 'other'", str(observed[1].message))
        self.assertEqual(list(table.index), ["sample-1", "sample-3"])

    def test_build_prince_input_filters_features_and_drops_empty_group(self):
        tables = {
            "metabolome": self.filter_table_a,
            "microbiome": self.filter_table_b,
            "empty": self.filter_drop_group,
        }

        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            table, groups = _build_prince_input(tables)

        observed_messages = [str(warning.message) for warning in observed]
        self.assertIn(
            "\033[33mDropped columns with missing values: "
            "metabolome:feature-missing\033[0m",
            observed_messages,
        )
        self.assertIn(
            "\033[33mDropped columns with zero variance: "
            "metabolome:feature-constant\033[0m",
            observed_messages,
        )
        self.assertIn(
            "\033[33mDropped columns with missing values: "
            "empty:feature-drop-missing\033[0m",
            observed_messages,
        )
        self.assertIn(
            "\033[33mDropped columns with zero variance: "
            "empty:feature-drop-constant\033[0m",
            observed_messages,
        )
        self.assertIn(
            "\033[33mDropped MFA group 'empty' because all features were removed "
            "during missing value filtering or zero-variance filtering.\033[0m",
            observed_messages,
        )
        self.assertEqual(
            list(table.columns),
            [
                "metabolome:feature-a1",
                "metabolome:feature-a2",
                "microbiome:feature-b1",
                "microbiome:feature-b2",
            ],
        )
        self.assertEqual(
            groups,
            {
                "metabolome": [
                    "metabolome:feature-a1",
                    "metabolome:feature-a2",
                ],
                "microbiome": [
                    "microbiome:feature-b1",
                    "microbiome:feature-b2",
                ],
            },
        )

    def test_build_prince_input_error_no_groups(self):
        with self.assertRaisesRegex(ValueError, "at least two groups"):
            _build_prince_input()

    def test_build_prince_input_error_one_table_group(self):
        with self.assertRaisesRegex(ValueError, "at least two groups"):
            _build_prince_input({"metabolome": self.table_a})

    def test_build_prince_input_error_illegal_group_name(self):
        with self.assertRaisesRegex(ValueError, "cannot contain ':'"):
            _build_prince_input({"illegal:name": self.table_a, "other": self.table_b})

    def test_build_prince_input_error_no_shared_samples(self):
        with self.assertRaisesRegex(ValueError, "do not share any sample IDs"):
            _build_prince_input({"metabolome": self.table_a, "other": self.disjoint})

    def test_build_prince_input_uses_two_metadata_groups(self):
        table, groups = _build_prince_input(
            sample_metadata=self.sample_metadata,
            metadata_groups={"clinical": "age,score", "body": "bmi"},
        )

        self.assertIn("clinical:age", table.columns)
        self.assertIn("clinical:score", table.columns)
        self.assertIn("body:bmi", table.columns)
        self.assertEqual(groups["clinical"], ["clinical:age", "clinical:score"])
        self.assertEqual(groups["body"], ["body:bmi"])
        self.assertEqual(
            list(table.index), ["sample-1", "sample-2", "sample-3", "sample-4"]
        )

    def test_build_prince_input_error_string_metadata_group_is_one_group(self):
        with self.assertRaisesRegex(ValueError, "at least two groups"):
            _build_prince_input(
                sample_metadata=self.sample_metadata,
                metadata_groups="clinical",
            )

    def test_build_prince_input_does_not_parse_string_metadata_mapping(self):
        with self.assertRaisesRegex(ValueError, "cannot contain ':'"):
            _build_prince_input(
                sample_metadata=self.sample_metadata,
                metadata_groups="clinical:age,bmi",
            )

    def test_build_prince_input_error_unknown_metadata_column(self):
        with self.assertRaisesRegex(ValueError, "not present in the metadata: nope"):
            _build_prince_input(
                {"metabolome": self.table_a},
                self.sample_metadata,
                {"clinical": "nope"},
            )

    def test_build_prince_input_error_duplicate_metadata_column(self):
        with self.assertRaisesRegex(
            ValueError, "cannot be assigned to multiple groups: age"
        ):
            _build_prince_input(
                {"metabolome": self.table_a},
                self.sample_metadata,
                {"clinical": "age", "body": "age"},
            )

    def test_build_prince_input_error_metadata_groups_without_metadata(self):
        with self.assertRaisesRegex(
            ValueError, "metadata_groups requires sample_metadata"
        ):
            _build_prince_input(
                {"metabolome": self.table_a},
                metadata_groups={"clinical": "age"},
            )

    def test_build_prince_input_error_group_duplicates(self):
        with self.assertRaisesRegex(
            ValueError, "cannot duplicate feature table group names: metabolome"
        ):
            _build_prince_input(
                {"metabolome": self.table_a},
                self.sample_metadata,
                {"metabolome": "age"},
            )

    def test_mfa_parses_prince_values_and_names(self):
        tables = {"metabolome": self.table_a, "microbiome": self.table_b}
        metadata_groups = {"clinical": "age,bmi"}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results = mfa(
                tables=tables,
                sample_metadata=self.sample_metadata,
                metadata_groups=metadata_groups,
                engine="scipy",
            )

            table, groups = _build_prince_input(
                tables,
                self.sample_metadata,
                metadata_groups,
            )
        prince_result = prince.MFA(engine="scipy").fit(table, groups=groups)

        results.validate()
        ordn = results.ordination.view(OrdinationResults)
        prince_samples = prince_result.row_coordinates(table)
        prince_features = prince_result.column_coordinates_
        self.assertIsInstance(results, ComponentAnalysisDirFmt)
        self.assertIsInstance(ordn, OrdinationResults)

        npt.assert_allclose(ordn.samples.to_numpy(), prince_samples.to_numpy())
        npt.assert_allclose(ordn.features.to_numpy(), prince_features.to_numpy())
        npt.assert_allclose(ordn.eigvals.to_numpy(), prince_result.eigenvalues_)
        npt.assert_allclose(
            ordn.proportion_explained.to_numpy(),
            prince_result.percentage_of_variance_,
        )
        self._assert_prince_table_written(
            results,
            results.partial_sample_coordinates,
            prince_result.partial_row_coordinates(table),
        )
        self._assert_prince_table_written(
            results,
            results.sample_cosine_similarities,
            prince_result.row_cosine_similarities(table),
        )
        self._assert_prince_table_written(
            results,
            results.sample_contributions,
            prince_result.row_contributions_,
        )
        self._assert_prince_table_written(
            results,
            results.group_coordinates,
            prince_result.group_coordinates_,
        )
        self._assert_prince_table_written(
            results,
            results.group_contributions,
            prince_result.group_contributions_,
        )
        self._assert_prince_table_written(
            results,
            results.group_cosine_similarities,
            prince_result.group_cosine_similarities_,
        )
        self._assert_prince_table_written(
            results,
            results.partial_correlations,
            prince_result.partial_correlations_,
        )
        self._assert_prince_table_written(
            results,
            results.partial_contributions,
            prince_result.partial_contributions_,
        )
        self._assert_prince_table_written(
            results,
            results.feature_correlations,
            prince_result.column_correlations,
        )
        self._assert_prince_table_written(
            results,
            results.feature_contributions,
            prince_result.column_contributions_,
        )
        self._assert_prince_table_written(
            results,
            results.feature_cosine_similarities,
            prince_result.column_cosine_similarities_,
        )

    def test_mfa_filters_missing_and_zero_variance_features(self):
        tables = {
            "metabolome": self.filter_table_a,
            "microbiome": self.filter_table_b,
        }

        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            results = mfa(tables=tables, engine="scipy")

        observed_messages = [str(warning.message) for warning in observed]
        self.assertIn(
            "\033[33mDropped columns with missing values: "
            "metabolome:feature-missing\033[0m",
            observed_messages,
        )
        self.assertIn(
            "\033[33mDropped columns with zero variance: "
            "metabolome:feature-constant\033[0m",
            observed_messages,
        )

        ordination = results.ordination.view(OrdinationResults)
        self.assertEqual(
            list(ordination.features.index),
            [
                "metabolome:feature-a1",
                "metabolome:feature-a2",
                "microbiome:feature-b1",
                "microbiome:feature-b2",
            ],
        )
