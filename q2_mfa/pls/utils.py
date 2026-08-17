# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import platform
import re
import warnings

import numpy as np
import pandas as pd
from q2_types.tabular import TableJSONLFileFormat
from q2_types.tabular._deferred_setup._transformers import table_jsonl_to_df
from rachis.core.exceptions import RachisWarning
from rachis.plugin import CaptureHolder
from rpy2.robjects import (
    ListVector,
    StrVector,
    conversion,
    default_converter,
    pandas2ri,
    r,
)
from rpy2.robjects.conversion import localconverter


def _resolve_ncomp(
    ncomp: CaptureHolder[int], tuned_components, weighted, measure, distance
) -> int:
    """Captures a manual ncomp or derives it from a components artifact."""
    manual_ncomp = ncomp is not None and (
        not isinstance(ncomp, CaptureHolder) or ncomp.is_set
    )
    if manual_ncomp and tuned_components is not None:
        raise ValueError(
            "Provide either ncomp or a tuned-components artifact, not both."
        )
    return CaptureHolder.get_or_set(
        ncomp,
        lambda: _ncomp_from_tuned_components(
            tuned_components, weighted, measure, distance
        ),
    )


def _ncomp_from_tuned_components(tuned_components, weighted, measure, distance) -> int:
    """Reads the component count chosen for the requested criterion."""
    if tuned_components is None:
        raise ValueError("Provide ncomp or a tuned-components artifact.")
    matrix = table_jsonl_to_df(
        TableJSONLFileFormat(tuned_components.choice_matrix.path_maker(), mode="r")
    )
    vote = "weighted" if weighted else "majority"
    requested_measure = "Overall.BER" if measure == "BER" else "Overall.ER"
    selected = matrix.loc[
        (matrix["vote"] == vote)
        & (matrix["measure"] == requested_measure)
        & (matrix["distance"] == distance),
        "ncomp",
    ]
    if len(selected) != 1:
        raise ValueError(
            "The component-tuning artifact has no unique choice for the "
            "requested vote, measure, and distance."
        )
    return int(selected.iloc[0])


def _align_samples(tables: dict, y) -> tuple[dict[str, pd.DataFrame], pd.Series]:
    """Intersects input-table and categorical-target sample IDs.

    Args:
        tables (dict): Named input tables from a QIIME collection.
        y: Categorical metadata column.

    Returns:
        tuple[dict[str, pd.DataFrame], pd.Series]: Aligned blocks and target.

    Raises:
        ValueError: If the inputs have no shared samples or the target is missing.
    """
    blocks = dict(getattr(tables, "collection", tables))
    target = y.to_series().copy()
    if not blocks:
        raise ValueError("block-splsda requires at least two named feature tables.")
    if len(blocks) < 2:
        raise ValueError("block-splsda requires at least two named feature tables.")
    if target.isna().any():
        raise ValueError("The categorical target contains missing values.")

    shared = next(iter(blocks.values())).index
    for table in list(blocks.values())[1:] + [target.to_frame()]:
        shared = shared.intersection(table.index)
    if shared.empty:
        raise ValueError("DIABLO inputs do not share any sample IDs.")

    aligned = {}
    for name, table in blocks.items():
        dropped = table.index.difference(shared)
        if not dropped.empty:
            warnings.warn(
                f"Dropping samples from block '{name}' that are not shared "
                f"across all DIABLO inputs:\n{', '.join(map(str, dropped))}",
                RachisWarning,
                stacklevel=2,
            )
        aligned[str(name)] = table.loc[shared].copy()
    dropped = target.index.difference(shared)
    if not dropped.empty:
        warnings.warn(
            "Dropping target metadata samples that are not shared across all "
            f"DIABLO inputs:\n{', '.join(map(str, dropped))}",
            RachisWarning,
            stacklevel=2,
        )
    return aligned, target.loc[shared].copy()


def _resolve_design(
    design_matrix, design_weight: float | None, block_names: list[str]
) -> pd.DataFrame | float:
    """Validates explicit design metadata or passes through a scalar design.

    Args:
        design_matrix: Optional Metadata-encoded matrix.
        design_weight (float | None): Scalar design weight for mixOmics.
        block_names (list[str]): Input-table collection keys.

    Returns:
        pd.DataFrame | float: Validated matrix or scalar weight for mixOmics.

    Raises:
        ValueError: If neither or both design representations are supplied, or
            explicit metadata is not a valid block design matrix.
    """
    if (design_matrix is None) == (design_weight is None):
        raise ValueError(
            "Provide exactly one of design_matrix or design_weight for DIABLO."
        )
    if design_weight is not None:
        return design_weight

    matrix = design_matrix.to_dataframe().copy()
    expected = set(block_names)
    if set(matrix.index) != expected or set(matrix.columns) != expected:
        raise ValueError(
            "Design matrix row and column names must exactly match the input "
            "feature-table collection names."
        )
    matrix = matrix.loc[block_names, block_names]
    try:
        matrix = matrix.astype(float)
    except (TypeError, ValueError) as error:
        raise ValueError("Design matrix values must be numeric.") from error
    if not np.allclose(matrix.to_numpy(), matrix.to_numpy().T):
        raise ValueError("Design matrix must be symmetrical.")
    if not np.allclose(np.diag(matrix.to_numpy()), 0):
        raise ValueError("Design matrix diagonal must contain only zeroes.")
    return matrix


def _parse_keep_x(keep_x: dict, block_names: list[str], ncomp: int, tune_keepx: bool):
    """Parses a named keepX grid or exact final feature counts.

    Args:
        keep_x (dict): Collection mapping blocks to comma-separated integers.
        block_names (list[str]): Expected input-table collection keys.
        ncomp (int): Number of components in the final fitted model.
        tune_keepx (bool): Whether values represent tuning candidates.

    Returns:
        dict[str, list[int]]: Parsed tune candidates or final ``keepX`` values.

    Raises:
        ValueError: If no values are supplied, their keys are wrong, or exact
            final values do not provide one count per component.
    """
    if keep_x is None:
        raise ValueError("keep_x is required for DIABLO variable selection.")
    values = dict(getattr(keep_x, "collection", keep_x))
    if set(values) != set(block_names):
        raise ValueError(
            "keep_x collection keys must exactly match the input feature-table "
            "collection names."
        )
    try:
        parsed = {
            name: [int(value.strip()) for value in str(values[name]).split(",")]
            for name in block_names
        }
    except ValueError as error:
        raise ValueError(
            "Each keep_x collection value must be a comma-separated integer list."
        ) from error
    if not tune_keepx:
        invalid_blocks = [
            name for name, counts in parsed.items() if len(counts) != ncomp
        ]
        if invalid_blocks:
            raise ValueError(
                "When tune_keepx is False, each keep_x value must provide "
                f"exactly {ncomp} comma-separated counts, one for each final "
                f"component. Invalid blocks: {', '.join(invalid_blocks)}."
            )
    return parsed


def _build_bpparam(threads: int, seed: int):
    """Loads BiocParallel and creates an OS-appropriate backend.

    Args:
        threads (int): Requested workers, or 0 for BiocParallel's default.
        seed (int): Reproducible BiocParallel random-number seed.

    Returns:
        object: R SerialParam, SnowParam, or MulticoreParam backend.
    """
    r("suppressPackageStartupMessages(library(BiocParallel))")
    if threads == 1:
        return r["SerialParam"](**{"RNGseed": seed})
    kwargs = {"RNGseed": seed}
    if threads > 1:
        kwargs["workers"] = threads
    if platform.system() == "Windows":
        return r["SnowParam"](**{"type": "SOCK", **kwargs})
    return r["MulticoreParam"](**kwargs)


def _quiet_tune_block_splsda(*args, **kwargs):
    """Runs mixOmics tuning without its status output or warnings."""
    quiet_tune = r(
        "function(...) { "
        "output <- tempfile(); sink(output); "
        "on.exit({ sink(); unlink(output) }, add = TRUE); "
        "suppressWarnings(suppressMessages(tune.block.splsda(...))) "
        "}"
    )
    return quiet_tune(*args, **kwargs)


def _to_r_inputs(blocks, target, design):
    """Converts aligned pandas inputs to named R objects with preserved labels.

    Args:
        blocks: Named pandas input tables.
        target: Aligned categorical target series.
        design: Validated pandas design matrix.

    Returns:
        tuple: Named R block list, factor target, and design matrix.
    """
    with localconverter(default_converter + pandas2ri.converter):
        r_blocks = ListVector(
            {name: conversion.py2rpy(table) for name, table in blocks.items()}
        )
        r_design = conversion.py2rpy(design)
    r_target = r["factor"](StrVector(target.astype(str).tolist()))
    r_target.names = StrVector(target.index.astype(str).tolist())
    return r_blocks, r_target, r_design


def _r_named_frames(values) -> dict[str, pd.DataFrame]:
    """Converts a named R list of tables to a pandas mapping.

    Args:
        values: Named R list containing mixOmics table-like outputs.

    Returns:
        dict[str, pd.DataFrame]: Table name to pandas DataFrame mapping.
    """
    if type(values).__name__ == "NULLType":
        return {}
    try:
        names = list(values.names)
    except TypeError:
        return {}
    if not names:
        table = _r_to_dataframe(values)
        return {} if table is None else {"overall": table}
    return {str(name): _r_to_dataframe(value) for name, value in zip(names, values)}


def _r_to_dataframe(value) -> pd.DataFrame | None:
    """Converts an R vector, matrix, or data frame while preserving labels."""
    if type(value).__name__ == "NULLType":
        return None
    row_names = r["rownames"](value)
    column_names = r["colnames"](value)
    value_names = r["names"](value)
    row_labels = (
        [str(label) for label in row_names]
        if type(row_names).__name__ != "NULLType"
        else None
    )
    column_labels = (
        [str(label) for label in column_names]
        if type(column_names).__name__ != "NULLType"
        else None
    )
    value_labels = (
        [str(label) for label in value_names]
        if type(value_names).__name__ != "NULLType"
        else None
    )
    with localconverter(default_converter + pandas2ri.converter):
        converted = conversion.rpy2py(value)
    if isinstance(converted, pd.DataFrame):
        if row_labels is not None and len(row_labels) == len(converted.index):
            converted.index = row_labels
        if column_labels is not None and len(column_labels) == len(converted.columns):
            converted.columns = column_labels
        return converted
    if isinstance(converted, pd.Series):
        if value_labels is not None and len(value_labels) == len(converted.index):
            converted.index = value_labels
        return converted.to_frame(name=converted.name or "value")
    array = np.asarray(converted)
    if array.ndim == 0:
        return pd.DataFrame({"value": [array.item()]})
    if array.ndim == 1:
        index = (
            value_labels if value_labels and len(value_labels) == len(array) else None
        )
        return pd.DataFrame({"value": array}, index=index)
    index = row_labels if row_labels and len(row_labels) == len(array) else None
    columns = (
        column_labels
        if column_labels and len(column_labels) == array.shape[1]
        else None
    )
    return pd.DataFrame(array, index=index, columns=columns)


def _r_ave_frames(values) -> dict[str, pd.DataFrame]:
    """Converts mixOmics AVE summaries into explicit component records.

    Args:
        values: Named R list containing AVE_X, AVE_outer, and AVE_inner.

    Returns:
        dict[str, pd.DataFrame]: AVE summary names mapped to already-long
            tables with block, component, and value columns as appropriate.
    """
    if type(values).__name__ == "NULLType":
        return {}
    ave_x = values.rx2("AVE_X")
    ave_x_frames = []
    for block_name, component_values in zip(ave_x.names, ave_x):
        values_array = np.asarray(component_values, dtype=float)
        ave_x_frames.append(
            pd.DataFrame(
                {
                    "block": str(block_name),
                    "component": np.arange(len(values_array)),
                    "value": values_array,
                }
            )
        )

    def component_vector(name: str) -> pd.DataFrame:
        component_values = np.asarray(values.rx2(name), dtype=float)
        return pd.DataFrame(
            {
                "component": np.arange(len(component_values)),
                "value": component_values,
            }
        )

    return {
        "AVE_X": pd.concat(ave_x_frames, ignore_index=True),
        "AVE_outer": component_vector("AVE_outer"),
        "AVE_inner": component_vector("AVE_inner"),
    }


def _r_criterion_to_dataframe(values) -> pd.DataFrame | None:
    """Flattens per-component convergence traces into one pandas table.

    Args:
        values: Unnamed R list of numeric convergence criteria, one per
            component.

    Returns:
        pd.DataFrame | None: Component, iteration, and criterion values, or
        None when mixOmics did not return convergence criteria.
    """
    if type(values).__name__ == "NULLType":
        return None
    traces = []
    for component, trace in enumerate(values):
        trace_values = np.asarray(trace, dtype=float)
        traces.append(
            pd.DataFrame(
                {
                    "component": component,
                    "iteration": np.arange(1, len(trace_values) + 1),
                    "criterion": trace_values,
                }
            )
        )
    return pd.concat(traces, ignore_index=True) if traces else None


def _r_feature_stability_to_dataframe(perf_result) -> pd.DataFrame | None:
    """Averages final-model selection frequencies across CV repeats.

    Args:
        perf_result: R ``perf`` result for the final block sPLS-DA model.

    Returns:
        pd.DataFrame | None: Block, feature, component, and mean selection
            frequency records, or None when mixOmics did not return stability.
    """
    stable = perf_result.rx2("features").rx2("stable")
    if type(stable).__name__ == "NULLType":
        return None
    records = []
    for repeat_values in stable:
        for block_name, component_values in zip(repeat_values.names, repeat_values):
            for component, selection_frequency in enumerate(component_values):
                feature_names = [str(name) for name in r["names"](selection_frequency)]
                records.append(
                    pd.DataFrame(
                        {
                            "block": str(block_name),
                            "feature": feature_names,
                            "component": component,
                            "selection_frequency": np.asarray(
                                selection_frequency, dtype=float
                            ),
                        }
                    )
                )
    if not records:
        return None
    return (
        pd.concat(records, ignore_index=True)
        .groupby(["block", "feature", "component"], as_index=False)
        .selection_frequency.mean()
        .rename(columns={"selection_frequency": "mean_selection_frequency"})
    )


def _r_auc_to_dataframe(perf_result) -> pd.DataFrame:
    """Converts mixOmics per-component, per-contrast AUC results.

    Args:
        perf_result: R ``perf`` result for the final block sPLS-DA model.

    Returns:
        pd.DataFrame: Component, contrast, AUC, and p-value records.
    """
    auc = perf_result.rx2("auc")
    columns = ["component", "contrast", "auc", "p_value"]
    if type(auc).__name__ == "NULLType":
        return pd.DataFrame(columns=columns)
    records = []
    for component, values in enumerate(auc):
        auc_table = pd.DataFrame(
            np.asarray(values),
            index=[str(name) for name in r["rownames"](values)],
            columns=[str(name) for name in r["colnames"](values)],
        )
        records.append(
            pd.DataFrame(
                {
                    "component": component,
                    "contrast": auc_table.index,
                    "auc": auc_table["AUC"].to_numpy(),
                    "p_value": auc_table["p-value"].to_numpy(),
                }
            )
        )
    return (
        pd.concat(records, ignore_index=True)
        if records
        else pd.DataFrame(columns=columns)
    )


def _r_weighted_vote_error_rate_to_dataframe(perf_result) -> pd.DataFrame:
    """Converts weighted-vote mean and SD error rates to long-form records.

    Args:
        perf_result: R ``perf`` result for the final block sPLS-DA model.

    Returns:
        pd.DataFrame: Distance, class, component, statistic, and error-rate
            records.
    """
    columns = ["distance", "class", "component", "statistic", "value"]
    tables = [
        _r_weighted_vote_error_rate_statistic_to_dataframe(
            perf_result.rx2("WeightedVote.error.rate"), "mean"
        ),
        _r_weighted_vote_error_rate_statistic_to_dataframe(
            perf_result.rx2("WeightedVote.error.rate.sd"), "sd"
        ),
    ]
    tables = [table for table in tables if not table.empty]
    return (
        pd.concat(tables, ignore_index=True)
        if tables
        else pd.DataFrame(columns=columns)
    )


def _r_weighted_vote_error_rate_statistic_to_dataframe(
    error_rates, statistic: str
) -> pd.DataFrame:
    """Converts one weighted-vote error-rate statistic to long-form records.

    Args:
        error_rates: Named R list of distance-specific error-rate matrices.
        statistic: Long-form statistic label, either ``mean`` or ``sd``.

    Returns:
        pd.DataFrame: Distance, class, component, statistic, and value records.
    """
    columns = ["distance", "class", "component", "statistic", "value"]
    if type(error_rates).__name__ == "NULLType":
        return pd.DataFrame(columns=columns)
    records = []
    for distance, rates in zip(error_rates.names, error_rates):
        values = np.asarray(rates, dtype=float)
        class_names = [str(name) for name in r["rownames"](rates)]
        for component in range(values.shape[1]):
            records.append(
                pd.DataFrame(
                    {
                        "distance": str(distance),
                        "class": class_names,
                        "component": component,
                        "statistic": statistic,
                        "value": values[:, component],
                    }
                )
            )
    return (
        pd.concat(records, ignore_index=True)
        if records
        else pd.DataFrame(columns=columns)
    )


def _r_feature_selection_error_rate_to_dataframe(tune_result) -> pd.DataFrame:
    """Converts tuning mean and SD error rates to long-form records.

    Args:
        tune_result: R ``tune.block.splsda`` result.

    Returns:
        pd.DataFrame: KeepX combination, component, statistic, and error-rate
            records.
    """
    columns = ["keepx", "component", "statistic", "value"]
    tables = [
        _r_feature_selection_error_rate_statistic_to_dataframe(
            tune_result.rx2("error.rate"), "mean"
        ),
        _r_feature_selection_error_rate_statistic_to_dataframe(
            tune_result.rx2("error.rate.sd"), "sd"
        ),
    ]
    tables = [table for table in tables if not table.empty]
    return (
        pd.concat(tables, ignore_index=True)
        if tables
        else pd.DataFrame(columns=columns)
    )


def _expand_keepx_columns(
    error_rates: pd.DataFrame, block_names: list[str] | tuple[str, ...]
) -> pd.DataFrame:
    """Replaces positional keepX labels with one named column per block."""
    block_names = tuple(block_names)
    expected = {"keepx", "component", "statistic", "value"}
    missing = expected.difference(error_rates.columns)
    if missing:
        raise ValueError(
            "Feature-selection error rates are missing required columns: "
            f"{', '.join(sorted(missing))}."
        )
    keepx_columns = [f"keepx_{name}" for name in block_names]
    parsed = error_rates["keepx"].map(
        lambda value: [int(count) for count in str(value).split("_")]
    )
    if any(len(values) != len(block_names) for values in parsed):
        raise ValueError(
            "Feature-selection keepX labels do not match the input block count."
        )
    result = error_rates.drop(columns="keepx").copy()
    result[keepx_columns] = pd.DataFrame(parsed.tolist(), index=result.index)
    return result[["component", "statistic", "value", *keepx_columns]]


def _r_feature_selection_error_rate_statistic_to_dataframe(
    error_rates, statistic: str
) -> pd.DataFrame:
    """Converts one tuning error-rate statistic matrix to long-form records.

    Args:
        error_rates: R matrix of tested keepX combinations by component.
        statistic: Long-form statistic label, either ``mean`` or ``sd``.

    Returns:
        pd.DataFrame: KeepX combination, component, statistic, and value
            records.
    """
    columns = ["keepx", "component", "statistic", "value"]
    if type(error_rates).__name__ == "NULLType":
        return pd.DataFrame(columns=columns)
    values = np.asarray(error_rates, dtype=float)
    keepx_values = [str(value) for value in r["dimnames"](error_rates)[0]]
    component_names = [str(value) for value in r["dimnames"](error_rates)[1]]
    component_numbers = []
    for position, name in enumerate(component_names):
        match = re.fullmatch(r"comp(\d+)", name)
        component_numbers.append(int(match.group(1)) - 1 if match else position)
    records = []
    for position, component in enumerate(component_numbers):
        records.append(
            pd.DataFrame(
                {
                    "keepx": keepx_values,
                    "component": component,
                    "statistic": statistic,
                    "value": values[:, position],
                }
            )
        )
    return (
        pd.concat(records, ignore_index=True)
        if records
        else pd.DataFrame(columns=columns)
    )
