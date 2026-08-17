# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import shutil
from pathlib import Path

import pandas as pd
from q2_types.tabular._deferred_setup._transformers import df_to_table_jsonl

from q2_mfa.plugin_setup import plugin

from ._format import PLSFeatureSelectionDirFmt
from ._tune_result import _PLSFeatureSelectionResult


@plugin.register_transformer
def _pls_feature_selection_to_dirfmt(
    result: _PLSFeatureSelectionResult,
) -> PLSFeatureSelectionDirFmt:
    directory_format = PLSFeatureSelectionDirFmt()
    _write_table(
        directory_format.error_rate.path_maker(),
        result.error_rate,
    )
    _write_table(
        directory_format.selected_features.path_maker(), result.selected_features
    )
    return directory_format


def _write_table(path: Path, table: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = table.convert_dtypes()
    records.attrs["description"] = "mixOmics DIABLO tuning output table."
    for column in records.columns:
        records[column].attrs["description"] = ""
    jsonl = df_to_table_jsonl(records)
    shutil.copyfile(str(jsonl), path)
