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


class NumericTSVFormat(model.TextFileFormat):
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
            df = pd.read_csv(str(self), sep="\t", dtype=str, keep_default_na=True)
        except pd.errors.EmptyDataError as exc:
            raise ValidationError("File is empty.") from exc

        header = list(df.columns)
        if "id" not in header:
            raise ValidationError(
                f"Invalid header for Numeric TSV: {header}, must contain 'id'."
            )

        value_columns = [column for column in header if column != "id"]
        if len(value_columns) < 1:
            raise ValidationError(
                "Expected at least 1 Numeric TSV value column, observed 0."
            )

        values = df[value_columns]
        numeric_values = values.apply(pd.to_numeric, errors="coerce")
        if numeric_values.isna().mask(values.isna(), False).to_numpy().any():
            raise ValidationError("Numeric TSV value columns must be numeric.")


class ComponentAnalysisDirFmt(model.DirectoryFormat):
    ordination = model.File("ordination.txt", format=OrdinationFormat)
    partial_sample_coordinates = model.File(
        "partial-sample-coordinates.tsv", format=NumericTSVFormat, optional=True
    )
    sample_cosine_similarities = model.File(
        "sample-cosine-similarities.tsv", format=NumericTSVFormat
    )
    sample_contributions = model.File(
        "sample-contributions.tsv", format=NumericTSVFormat
    )
    group_coordinates = model.File(
        "group-coordinates.tsv", format=NumericTSVFormat, optional=True
    )
    group_contributions = model.File(
        "group-contributions.tsv", format=NumericTSVFormat, optional=True
    )
    group_cosine_similarities = model.File(
        "group-cosine-similarities.tsv", format=NumericTSVFormat, optional=True
    )
    partial_correlations = model.File(
        "partial-correlations.tsv", format=NumericTSVFormat, optional=True
    )
    partial_contributions = model.File(
        "partial-contributions.tsv", format=NumericTSVFormat, optional=True
    )
    feature_correlations = model.File(
        "feature-correlations.tsv", format=NumericTSVFormat
    )
    feature_contributions = model.File(
        "feature-contributions.tsv", format=NumericTSVFormat
    )
    feature_cosine_similarities = model.File(
        "feature-cosine-similarities.tsv", format=NumericTSVFormat
    )
