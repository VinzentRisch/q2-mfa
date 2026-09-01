# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import platform
import warnings

import numpy as np
import pandas as pd
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

from q2_mfa.pls.types._format import PLSTuneComponentsDirFmt


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
    target = y.to_series().copy() if hasattr(y, "to_series") else y.copy()
    if len(blocks) < 2:
        raise ValueError("At least two named feature tables are required.")
    target = target.dropna()
    blocks = {**blocks, "y": target.to_frame()}

    shared = next(iter(blocks.values())).index
    for table in list(blocks.values())[1:]:
        shared = shared.intersection(table.index)
    if shared.empty:
        raise ValueError("The input feature tables and response share no sample IDs.")

    aligned = {}
    for name, table in blocks.items():
        dropped = table.index.difference(shared)
        if not dropped.empty:
            warnings.warn(
                f"Dropping samples from block '{name}' that are not shared "
                f"across all blocks:\n{', '.join(map(str, dropped))}",
                RachisWarning,
                stacklevel=2,
            )
        aligned[str(name)] = table.loc[shared].copy()
    target = aligned.pop("y").iloc[:, 0]
    return aligned, target


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
        raise ValueError("Provide exactly one of 'design-matrix' or 'design-weight'.")
    if design_weight is not None:
        return design_weight

    matrix = design_matrix.to_dataframe().copy()
    expected = set(block_names)
    if set(matrix.index) != expected or set(matrix.columns) != expected:
        raise ValueError(
            "The row and column names in 'design-matrix' must exactly match "
            "feature-table collection names."
        )
    matrix = matrix.loc[block_names, block_names]
    try:
        matrix = matrix.astype(float)
    except (TypeError, ValueError) as error:
        raise ValueError("Values in 'design-matrix' must be numeric.") from error
    if not np.allclose(matrix.to_numpy(), matrix.to_numpy().T):
        raise ValueError("'design-matrix' must be symmetrical.")
    if not np.allclose(np.diag(matrix.to_numpy()), 0):
        raise ValueError("The diagonal of 'design-matrix' must contain only zeroes.")
    return matrix


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
            {
                name: conversion.get_conversion().py2rpy(table)
                for name, table in blocks.items()
            }
        )
        r_design = conversion.get_conversion().py2rpy(design)
    r_target = r["factor"](StrVector(target.astype(str).tolist()))
    r_target.names = StrVector(target.index.astype(str).tolist())
    return r_blocks, r_target, r_design


def _r_vote_error_rate_to_dataframe(perf_result: ListVector, vote: str) -> pd.DataFrame:
    """Converts mixOmics vote error-rate means and standard deviations to rows."""
    columns = ["distance", "class", "component", "mean", "sd"]
    records = {}
    for statistic, error_rates in (
        ("mean", perf_result.rx2(f"{vote}.error.rate")),
        ("sd", perf_result.rx2(f"{vote}.error.rate.sd")),
    ):
        if type(error_rates).__name__ == "NULLType":
            continue
        for distance, rates in zip(error_rates.names, error_rates):
            values = np.asarray(rates, dtype=float)
            class_names = [str(name) for name in r["rownames"](rates)]
            for class_name, class_values in zip(class_names, values):
                for component, value in enumerate(class_values):
                    key = (str(distance), class_name, component)
                    record = records.setdefault(
                        key,
                        {"distance": key[0], "class": key[1], "component": key[2]},
                    )
                    record[statistic] = value
    return pd.DataFrame(records.values(), columns=columns)


def _resolve_ncomp(
    ncomp: CaptureHolder[int],
    tuned_ncomp: PLSTuneComponentsDirFmt | None,
    weighted: bool,
    measure: str,
    distance: str,
) -> int:
    """
    Captures a manual component count or derives it from a tuning artifact.

    Uses a manually supplied ``ncomp`` when available; otherwise, reads the
    count selected by the requested voting, measure, and distance criteria from
    the component-tuning artifact. The resolved value is captured for action
    provenance.

    Args:
        ncomp (CaptureHolder[int] | int | None): Manually supplied component
            count or capture holder for the resolved value.
        tuned_ncomp (PLSTuneComponentsDirFmt | None): Component-tuning artifact
            used when no manual component count is supplied.
        weighted (bool): Whether to use the weighted rather than majority vote.
        measure (str): Requested prediction-error measure.
        distance (str): Requested prediction distance.

    Returns:
        int: The selected number of components.

    Raises:
        ValueError: If exactly one of a manual count and tuning artifact is not
            provided, or the artifact has no unique matching selection.
    """
    if isinstance(ncomp, CaptureHolder):
        manual_ncomp = ncomp.is_set
    else:
        manual_ncomp = ncomp is not None
    has_tuned_ncomp = tuned_ncomp is not None
    if manual_ncomp == has_tuned_ncomp:
        raise ValueError("Provide exactly one of ncomp or a tuned-ncomp artifact.")
    if manual_ncomp:
        return CaptureHolder.get_or_set(ncomp, lambda: None)
    if isinstance(ncomp, CaptureHolder):
        return CaptureHolder.get_or_set(
            ncomp,
            lambda: _ncomp_from_tuned_ncomp(tuned_ncomp, weighted, measure, distance),
        )
    return _ncomp_from_tuned_ncomp(tuned_ncomp, weighted, measure, distance)


def _ncomp_from_tuned_ncomp(
    tuned_ncomp: PLSTuneComponentsDirFmt,
    weighted: bool,
    measure: str,
    distance: str,
) -> int:
    """
    Reads the component count chosen for a requested tuning criterion.

    Reads the weighted- or majority-vote choice matrix from the current
    component-tuning artifact.

    Args:
        tuned_ncomp (PLSTuneComponentsDirFmt): Component-tuning artifact
            containing the selected component counts.
        weighted (bool): Whether to use the weighted rather than majority vote.
        measure (str): Requested prediction-error measure.
        distance (str): Requested prediction distance.

    Returns:
        int: The uniquely selected number of components.

    Raises:
        ValueError: If the artifact has no selected component for the requested
            vote, measure, and distance.
    """
    requested_measure = "Overall.BER" if measure == "BER" else "Overall.ER"
    matrix_file = (
        tuned_ncomp.choice_matrix_weighted
        if weighted
        else tuned_ncomp.choice_matrix_majority
    )
    matrix = matrix_file.view(pd.DataFrame)
    selected_ncomp = matrix.loc[matrix["id"] == requested_measure, distance].iloc[0]
    if pd.isna(selected_ncomp):
        raise ValueError(
            "The component-tuning artifact has no selected number of components for "
            "the requested vote, measure, and distance."
        )
    return int(selected_ncomp)
