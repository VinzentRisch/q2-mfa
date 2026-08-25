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
from rpy2.robjects import (
    ListVector,
    StrVector,
    conversion,
    default_converter,
    pandas2ri,
    r,
)
from rpy2.robjects.conversion import localconverter


def _align_samples(tables: dict, y) -> tuple[dict[str, pd.DataFrame], pd.Series]:
    """Intersects input-table and categorical-target sample IDs."""
    blocks = dict(getattr(tables, "collection", tables))
    target = y.to_series().copy()
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
    """Validates explicit design metadata or passes through a scalar design."""
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


def _build_bpparam(threads: int, seed: int):
    """Creates an OS-appropriate BiocParallel backend.

    A value of zero delegates worker selection to BiocParallel.
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
    """Converts aligned pandas inputs to named R objects with preserved labels."""
    with localconverter(default_converter + pandas2ri.converter):
        r_blocks = ListVector(
            {name: conversion.py2rpy(table) for name, table in blocks.items()}
        )
        r_design = conversion.py2rpy(design)
    r_target = r["factor"](StrVector(target.astype(str).tolist()))
    r_target.names = StrVector(target.index.astype(str).tolist())
    return r_blocks, r_target, r_design


def _r_vote_error_rate_to_dataframe(perf_result, vote: str) -> pd.DataFrame:
    """Converts one vote's mean and SD error rates to wide records."""
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
                        {
                            "distance": key[0],
                            "class": key[1],
                            "component": key[2],
                        },
                    )
                    record[statistic] = value

    return pd.DataFrame(records.values(), columns=columns)
