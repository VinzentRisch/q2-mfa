# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import numpy as np
import pandas as pd
from q2_types.feature_table import FeatureTable, Unconstrained
from q2_types.metadata import ImmutableMetadata
from rachis import Metadata, ResultCollection
from rachis.plugin import CaptureHolder
from rpy2.robjects import (
    IntVector,
    ListVector,
    StrVector,
    conversion,
    default_converter,
    pandas2ri,
    r,
)
from rpy2.robjects.conversion import localconverter

from q2_mfa.pls.types._format import PLSTuneComponentsDirFmt


def _align_samples_metadata(ctx, tables, metadata_column):
    """
    Aligns feature tables and a metadata column to shared samples.

    - Removes missing metadata values.
    - Identifies IDs shared by the remaining column and every feature table
    - Filters the metadata column to those IDs.
    - Filters and reorders every feature table to the metadata sample order.

    Args:
        ctx (Context): Pipeline execution context used to retrieve actions.
        tables (ResultCollection): Named unconstrained feature tables.
        metadata_column (MetadataColumn): Metadata column to align.

    Returns:
        tuple[ResultCollection, Metadata]: A tuple containing:
            - ResultCollection: Tables filtered to the shared sample IDs.
            - Metadata: Aligned metadata containing the supplied column.
    """
    filter_ids = ctx.get_action("feature_table", "filter_ids")
    metadata_column = metadata_column.drop_missing_values()
    shared_ids = metadata_column.get_ids()
    for table in tables.values():
        shared_ids.intersection_update(table.view(pd.DataFrame).index)
    if not shared_ids:
        raise ValueError("The feature tables and metadata column have no shared IDs.")
    shared_ids = [str(sample_id) for sample_id in shared_ids]
    metadata_column = metadata_column.filter_ids(shared_ids)
    aligned_metadata = Metadata(metadata_column.to_dataframe())
    sample_ids = aligned_metadata.to_dataframe().index.tolist()

    aligned_tables = {}
    for name, table in tables.items():
        (filtered_table,) = filter_ids(
            table=table,
            axis="sample",
            ids=shared_ids,
        )
        aligned_tables[name] = ctx.make_artifact(
            FeatureTable[Unconstrained],
            filtered_table.view(pd.DataFrame).loc[sample_ids],
        )
    return (
        ResultCollection(aligned_tables),
        ctx.make_artifact(ImmutableMetadata, aligned_metadata),
    )


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
    """
    Creates a BiocParallel backend.

    Uses a serial backend for one worker and a multicore backend otherwise. A
    thread count of zero leaves worker selection to BiocParallel.

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
    return r["MulticoreParam"](**kwargs)


def _to_r_inputs(blocks, target, design, keep_x: dict[str, list[int]] | None = None):
    """Converts aligned pandas inputs to named R objects with preserved labels.

    Args:
        blocks: Named pandas input tables.
        target: Aligned categorical target series.
        design: Validated pandas design matrix.
        keep_x: Optional parsed keepX candidate grids by block.

    Returns:
        tuple: Named R block list, factor target, design matrix, and optional
            named R keepX list.
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
    r_keep_x = (
        ListVector({name: IntVector(values) for name, values in keep_x.items()})
        if keep_x is not None
        else None
    )
    return r_blocks, r_target, r_design, r_keep_x


def _r_vote_error_rate_to_dataframe(perf_result: ListVector, vote: str) -> pd.DataFrame:
    """
    Converts mixOmics vote error-rate means and standard deviations to rows.

    Combines the requested vote's error-rate and standard-deviation matrices
    into one table with distance measure, class, component, mean, and standard
    deviation columns.

    Args:
        perf_result (rpy2.robjects.vectors.ListVector): Result returned by
            mixOmics ``perf()``.
        vote (str): Vote type to extract, such as ``WeightedVote`` or
            ``MajorityVote``.

    Returns:
        pd.DataFrame: Error-rate records for the requested vote.

    Raises:
        ValueError: If mixOmics did not provide either the mean or standard
            deviation error-rate matrix for the requested vote.
    """
    columns = ["distance", "class", "component", "mean", "sd"]
    records = {}
    for statistic, error_rates in (
        ("mean", perf_result.rx2(f"{vote}.error.rate")),
        ("sd", perf_result.rx2(f"{vote}.error.rate.sd")),
    ):
        if type(error_rates).__name__ == "NULLType":
            raise ValueError(
                f"mixOmics did not provide {statistic} error rates for {vote}."
            )
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
    manual_ncomp = ncomp.is_set
    has_tuned_ncomp = tuned_ncomp is not None
    if manual_ncomp == has_tuned_ncomp:
        raise ValueError("Provide exactly one of ncomp or a tuned-ncomp artifact.")
    return CaptureHolder.get_or_set(
        ncomp,
        lambda: _ncomp_from_tuned_ncomp(tuned_ncomp, weighted, measure, distance),
    )


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
