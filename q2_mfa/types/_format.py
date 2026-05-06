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


class PrinceWideTSVFormat(model.TextFileFormat):
    def _validate_(self, level):
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
        if "id" not in header:
            raise ValidationError(
                f"Invalid header for Prince wide TSV: {header}, must contain " "'id'."
            )

        value_columns = [column for column in header if column != "id"]
        if len(value_columns) < 1:
            raise ValidationError(
                "Expected at least 1 Prince wide TSV value column, " "observed 0."
            )

        df = pd.read_csv(str(self), sep="\t")
        if df.empty:
            raise ValidationError("Prince wide TSV must contain at least one data row.")

        numeric_values = df[value_columns].apply(pd.to_numeric, errors="coerce")
        if numeric_values.isna().to_numpy().any():
            raise ValidationError("Prince wide TSV value columns must be numeric.")


class MFAResultsDirFmt(model.DirectoryFormat):
    ordination = model.File("ordination.txt", format=OrdinationFormat)
    partial_sample_coordinates = model.File(
        "partial-sample-coordinates.tsv", format=PrinceWideTSVFormat
    )
    sample_cosine_similarities = model.File(
        "sample-cosine-similarities.tsv", format=PrinceWideTSVFormat
    )
    group_coordinates = model.File("group-coordinates.tsv", format=PrinceWideTSVFormat)
    group_contributions = model.File(
        "group-contributions.tsv", format=PrinceWideTSVFormat
    )
    group_cosine_similarities = model.File(
        "group-cosine-similarities.tsv", format=PrinceWideTSVFormat
    )
    partial_correlations = model.File(
        "partial-correlations.tsv", format=PrinceWideTSVFormat
    )
    partial_contributions = model.File(
        "partial-contributions.tsv", format=PrinceWideTSVFormat
    )
    feature_correlations = model.File(
        "feature-correlations.tsv", format=PrinceWideTSVFormat
    )
    feature_contributions = model.File(
        "feature-contributions.tsv", format=PrinceWideTSVFormat
    )
    feature_cosine_similarities = model.File(
        "feature-cosine-similarities.tsv", format=PrinceWideTSVFormat
    )
