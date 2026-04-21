# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd
import rachis.plugin.model as model
from q2_types.ordination import OrdinationFormat
from rachis.core.exceptions import ValidationError


class _RequiredHeaderTSVFormat(model.TextFileFormat):
    REQUIRED_COLUMNS = ()

    def _validate(self):
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

    def _validate_(self, level):
        self._validate()


class PartialScoresFormat(_RequiredHeaderTSVFormat):
    REQUIRED_COLUMNS = ("sample_id", "group", "dim", "coordinate")


class PartialAxesFormat(_RequiredHeaderTSVFormat):
    REQUIRED_COLUMNS = ("group", "partial_axis", "global_dim", "value")


class GroupSummaryFormat(_RequiredHeaderTSVFormat):
    REQUIRED_COLUMNS = ("group", "dim", "coordinate", "contribution", "cos2")


class MFAResultsDirFmt(model.DirectoryFormat):
    ordination = model.File("ordination.txt", format=OrdinationFormat)
    partial_scores = model.File("partial-scores.tsv", format=PartialScoresFormat)
    partial_axes = model.File("partial-axes.tsv", format=PartialAxesFormat)
    group_summary = model.File("group-summary.tsv", format=GroupSummaryFormat)
