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

from ._format import PLSFitDirFmt
from ._result import _PLSFitResult


@plugin.register_transformer
def _pls_fit_to_dirfmt(result: _PLSFitResult) -> PLSFitDirFmt:
    """Serializes DIABLO outputs into consolidated long-form JSONL tables.

    Args:
        result (_PLSFitResult): Final model and post-fit performance tables.

    Returns:
        PLSFitDirFmt: One JSONL table for each PLS result category.
    """
    directory_format = PLSFitDirFmt()
    _write_table(
        directory_format.loadings.path_maker(),
        _block_feature_values(result.loadings),
    )
    _write_optional_table(
        directory_format.loadings_star.path_maker(),
        _block_feature_values(result.loadings_star),
    )
    _write_table(
        directory_format.variates.path_maker(),
        _block_sample_values(result.variates),
    )
    _write_table(
        directory_format.prop_expl_var.path_maker(),
        _block_component_values(result.prop_expl_var),
    )
    _write_optional_table(
        directory_format.vip.path_maker(), _block_feature_values(result.vip)
    )
    _write_optional_table(directory_format.ave.path_maker(), _ave_values(result.ave))
    _write_optional_table(directory_format.crit.path_maker(), result.crit)
    _write_optional_table(
        directory_format.feature_stability.path_maker(), result.feature_stability
    )
    _write_table(directory_format.auc.path_maker(), result.auc)
    _write_table(directory_format.error_rate.path_maker(), result.error_rate)
    _write_table(
        directory_format.feature_component_correlation.path_maker(),
        result.feature_component_correlation,
    )
    _write_table(
        directory_format.feature_similarity.path_maker(), result.feature_similarity
    )
    return directory_format


def _write_optional_table(path: Path, table: pd.DataFrame | None) -> None:
    """Writes an optional table only when mixOmics returned records."""
    if table is not None and not table.empty:
        _write_table(path, table)


def _write_table(path: Path, table: pd.DataFrame) -> None:
    """Writes a pandas table as a TableJSONL file.

    Args:
        path (Path): Destination JSONL file path.
        table (pd.DataFrame): Final long-form records.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    records = table.convert_dtypes()
    records.attrs["description"] = "mixOmics block sPLS-DA output table."
    for column in records.columns:
        records[column].attrs["description"] = ""
    jsonl = df_to_table_jsonl(records)
    shutil.copyfile(str(jsonl), path)


def _block_feature_values(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Consolidates block loadings or VIP tables by feature and component."""
    return _block_wide_values(tables, "feature")


def _block_sample_values(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Consolidates block variate tables by sample and component."""
    return _block_wide_values(tables, "sample")


def _block_wide_values(
    tables: dict[str, pd.DataFrame], identifier: str
) -> pd.DataFrame:
    """Converts named wide component tables to one block-labelled table."""
    records = []
    for block, table in tables.items():
        working = table.copy()
        working.index.name = identifier
        long_table = working.reset_index().melt(
            id_vars=[identifier], var_name="component", value_name="value"
        )
        long_table["component"] = [
            component
            for component in range(working.shape[1])
            for _ in range(len(working))
        ]
        long_table.insert(0, "block", str(block))
        records.append(long_table)
    columns = ["block", identifier, "component", "value"]
    if not records:
        return pd.DataFrame(columns=columns)
    combined = pd.concat(records, ignore_index=True)[columns]
    combined[identifier] = combined[identifier].astype(str)
    return combined


def _block_component_values(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Consolidates per-block explained-variance vectors by component."""
    records = []
    for block, table in tables.items():
        working = table.copy()
        if working.shape[1] == 1:
            long_table = pd.DataFrame(
                {"component": working.index, "value": working.iloc[:, 0]}
            )
        elif working.shape[0] == 1:
            long_table = pd.DataFrame(
                {"component": working.columns, "value": working.iloc[0]}
            )
        else:
            raise ValueError(
                "mixOmics prop_expl_var must contain one value per component."
            )
        long_table["component"] = range(len(long_table))
        long_table.insert(0, "block", str(block))
        records.append(long_table)
    columns = ["block", "component", "value"]
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.concat(records, ignore_index=True)[columns]


def _ave_values(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Consolidates AVE metrics while retaining their metric and block labels."""
    records = []
    for metric, table in tables.items():
        working = table.copy()
        if "block" not in working:
            working.insert(0, "block", "overall")
        working.insert(0, "metric", metric)
        records.append(working[["metric", "block", "component", "value"]])
    columns = ["metric", "block", "component", "value"]
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.concat(records, ignore_index=True)[columns]
