# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import csv

import pandas as pd
import rachis.plugin.model as model
from q2_types.ordination import OrdinationFormat
from rachis.core.exceptions import ValidationError


class _RequiredHeaderTSVFormat(model.TextFileFormat):
    REQUIRED_COLUMNS = ()
    MIN_VALUE_COLUMNS = 0

    def _validate(self):
        expected_columns = None
        with open(str(self), newline="") as fh:
            reader = csv.reader(fh, delimiter="\t")
            for line_number, row in enumerate(reader, start=1):
                if not row:
                    continue

                if expected_columns is None:
                    expected_columns = len(row)
                elif len(row) != expected_columns:
                    raise ValidationError(
                        f"Line {line_number} has {len(row)} columns, "
                        f"expected {expected_columns}."
                    )

        try:
            df = pd.read_csv(str(self), sep="\t", nrows=1)
        except pd.errors.EmptyDataError as exc:
            raise ValidationError("File is empty.") from exc

        header = list(df.columns)
        if not set(header).issuperset(self.REQUIRED_COLUMNS):
            raise ValidationError(
                f"Invalid header: {header}, do not contain all headers in: "
                f"{list(self.REQUIRED_COLUMNS)}"
            )

        value_columns = [
            column for column in header if column not in self.REQUIRED_COLUMNS
        ]
        if len(value_columns) < self.MIN_VALUE_COLUMNS:
            raise ValidationError(
                f"Expected at least {self.MIN_VALUE_COLUMNS} value column(s), "
                f"observed {len(value_columns)}."
            )

    def _validate_(self, level):
        self._validate()


class PrinceWideTSVFormat(_RequiredHeaderTSVFormat):
    REQUIRED_COLUMNS = ("id",)
    MIN_VALUE_COLUMNS = 1


class PartialAxesFormat(_RequiredHeaderTSVFormat):
    REQUIRED_COLUMNS = (
        "group",
        "partial_component",
        "global_component",
        "correlation",
    )


class GroupSummaryFormat(_RequiredHeaderTSVFormat):
    REQUIRED_COLUMNS = ("group", "component", "coordinate", "contribution", "cos2")


class MFAResultsDirFmt(model.DirectoryFormat):
    ordination = model.File("ordination.txt", format=OrdinationFormat)
    partial_sample_coordinates = model.File(
        "partial-sample-coordinates.tsv", format=PrinceWideTSVFormat
    )
    sample_cosine_similarities = model.File(
        "sample-cosine-similarities.tsv", format=PrinceWideTSVFormat
    )
    partial_axes = model.File("partial-axes.tsv", format=PartialAxesFormat)
    group_summary = model.File("group-summary.tsv", format=GroupSummaryFormat)
    feature_correlations = model.File(
        "feature-correlations.tsv", format=PrinceWideTSVFormat
    )
    feature_contributions = model.File(
        "feature-contributions.tsv", format=PrinceWideTSVFormat
    )
    feature_cosine_similarities = model.File(
        "feature-cosine-similarities.tsv", format=PrinceWideTSVFormat
    )
