# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd

from q2_mfa.plugin_setup import plugin

from ._format import NumericTSVFormat


@plugin.register_transformer
def _dataframe_to_numeric_tsv(table: pd.DataFrame) -> NumericTSVFormat:
    ff = NumericTSVFormat()
    table = table.copy()
    if isinstance(table.index, pd.MultiIndex):
        table.index = [
            ":".join(str(value) for value in index_values)
            for index_values in table.index
        ]
    if isinstance(table.columns, pd.MultiIndex):
        table.columns = [
            ":".join(str(value) for value in column_values)
            for column_values in table.columns
        ]
    table.to_csv(str(ff), sep="\t", index=True, index_label="id")
    return ff
