# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import shutil

from q2_types.tabular._deferred_setup._transformers import df_to_table_jsonl

from q2_mfa.plugin_setup import plugin

from ._format import PLSTuneComponentsDirFmt
from ._tune_components_result import _PLSTuneComponentsResult


@plugin.register_transformer
def _tune_components_to_dirfmt(
    result: _PLSTuneComponentsResult,
) -> PLSTuneComponentsDirFmt:
    """Serializes DIABLO component-selection tables as Table JSONL."""
    directory_format = PLSTuneComponentsDirFmt()
    _write_table(
        directory_format.error_rate.path_maker(),
        result.error_rate,
    )
    _write_table(
        directory_format.choice_matrix.path_maker(),
        result.choice_matrix,
    )
    return directory_format


def _write_table(path, table):
    table = table.convert_dtypes()
    table.attrs["description"] = "mixOmics DIABLO component-selection output table."
    for column in table.columns:
        table[column].attrs["description"] = ""
    jsonl = df_to_table_jsonl(table)
    shutil.copyfile(str(jsonl), path)
