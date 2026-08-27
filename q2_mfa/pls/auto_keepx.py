# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
"""Adaptive coarse-to-fine ``keepX`` tuning for DIABLO.

This module contains the automatic keepX strategy used by the QIIME action.
"""
from dataclasses import dataclass
from itertools import product as cartesian_product
from math import ceil, floor, prod, sqrt
from typing import Callable, Literal

import numpy as np
import pandas as pd
from rpy2.rinterface_lib import callbacks
from rpy2.robjects import IntVector, ListVector, r

from q2_mfa.pls.utils import (
    _build_bpparam,
    _quiet_tune_block_splsda,
    _r_feature_selection_error_rate_to_dataframe,
    _to_r_inputs,
)


@dataclass(frozen=True)
class AdaptiveKeepXResult:
    """Selected counts and tuning results from adaptive grid refinement.

    Attributes:
        keep_x: Selected retained-feature counts by block and component.
        block_names: Input-block names in the order used by mixOmics.
        evaluation_cache: Unique component-wise keepX evaluations, keyed by
            component number and integer keepX tuples in ``block_names`` order.
    """

    keep_x: dict[str, list[int]]
    block_names: tuple[str, ...]
    evaluation_cache: dict[int, dict[tuple[int, ...], dict[str, float | int]]]


def adaptive_keepx_refinement(
    blocks: dict[str, pd.DataFrame],
    target: pd.Series,
    design: pd.DataFrame | float,
    ncomp: int,
    *,
    initial_keepx: dict[str, list[int]] | None = None,
    min_keepx: int = 5,
    max_keepx_fraction: float = 0.2,
    grid_size: int = 5,
    refinement_factor: float = 2.0,
    selection_rule: Literal["one_se", "absolute_margin"] = "one_se",
    ber_margin: float = 0.0,
    se_multiplier: float = 1.0,
    tol: float = 1e-6,
    max_iter: int = 100,
    near_zero_var: bool = True,
    scale: bool = True,
    validation: str = "Mfold",
    folds: int = 5,
    nrepeat: int = 3,
    signif_threshold: float = 0.01,
    distance: str = "centroids.dist",
    measure: str = "BER",
    weighted: bool = True,
    seed: int = 42,
    threads: int = 1,
    round_runner: (
        Callable[[int, dict[str, list[int]], dict[str, list[int]] | None], pd.DataFrame]
        | None
    ) = None,
) -> AdaptiveKeepXResult:
    """Tunes DIABLO ``keepX`` with a coarse-to-fine adaptive grid.

    Components are tuned sequentially. Each component receives its own
    coarse-to-fine grid; once all of its refinement rounds are complete, its
    selected counts are supplied through mixOmics' ``already.tested.X`` while
    the next component is tuned. Rather than accepting mixOmics' numerical
    minimum directly, each round identifies a near-optimal BER plateau and
    chooses its most interpretable candidate. A later round narrows around
    that sparse candidate or, optionally, the whole plateau. If an anchor
    lies on a grid edge, the next grid expands in that direction, but never
    beyond the number of features in its block.

    ``grid_size`` controls the initial candidate count per block and the
    number of local candidates around each selected component value in later
    rounds. A refinement grid can therefore contain more than ``grid_size``
    values when components select different values.

    Args:
        blocks: Named, sample-by-feature input data frames.
        target: Categorical target indexed by the same sample IDs as ``blocks``.
        design: DIABLO design matrix or scalar design weight.
        ncomp: Number of components to tune.
        initial_keepx: Optional user-supplied candidate grid used as the first
            grid for every component. When supplied, automatic first-grid
            construction settings are ignored.
        min_keepx: Smallest retained-feature count considered during refinement.
        max_keepx_fraction: Initial upper-bound fraction per block.
        grid_size: Initial and per-component local candidate count.
        refinement_factor: Finite factor greater than one used to shrink
            interior local intervals and expand intervals at a grid edge.
        selection_rule: ``one_se`` selects candidates within one standard
            error of minimum BER; ``absolute_margin`` uses ``ber_margin``.
        ber_margin: Non-negative acceptable absolute BER increase when using
            ``absolute_margin``.
        se_multiplier: Multiplier of the best model's SE accepted
            by the ``one_se`` rule for selection and refinement.
        tol: mixOmics convergence tolerance.
        max_iter: mixOmics maximum fitting iterations.
        near_zero_var: Whether mixOmics filters near-zero variance predictors.
        scale: Whether mixOmics scales every block.
        validation: mixOmics cross-validation scheme.
        folds: Cross-validation folds.
        nrepeat: Cross-validation repeats.
        signif_threshold: mixOmics component-significance threshold.
        distance: Prediction distance used while tuning.
        measure: Error measure used while tuning.
        weighted: Whether tuning uses weighted prediction performance.
        seed: Reproducible seed for mixOmics cross-validation.
        threads: Number of OS-appropriate BiocParallel workers.
        round_runner: Optional pipeline callback that evaluates one component
            and keepX subgrid, returning its long-form mean/SD error rates.
            When omitted, calls mixOmics directly.

    Returns:
        AdaptiveKeepXResult: Final component-wise counts and the unique
            component-wise evaluation cache.

    Raises:
        ValueError: If inputs do not have compatible sample IDs, a grid is too
            large, or refinement settings cannot retain every component value.
    """
    # Inputs are aligned by tune_block_splsda before automatic tuning.
    _validate_min_keepx_against_blocks(
        blocks,
        min_keepx,
    )

    callbacks.consolewrite_print = lambda message: print(message, end="")
    callbacks.consolewrite_warnerror = lambda message: print(message, end="")
    r("suppressPackageStartupMessages(library(mixOmics))")
    r("suppressPackageStartupMessages(library(BiocParallel))")
    bpparam = _build_bpparam(threads, seed)

    evaluation_cache = {}
    final_component_decisions = {}
    fixed_keep_x = {name: [] for name in blocks}

    print("Sequential adaptive keepX grid refinement\n", flush=True)
    for component in range(1, ncomp + 1):
        grid = (
            {name: values.copy() for name, values in initial_keepx.items()}
            if initial_keepx is not None
            else _initial_grids(blocks, min_keepx, max_keepx_fraction, grid_size)
        )
        print(f"Tune component {component} of {ncomp}\n", flush=True)
        if component > 1:
            print("Fixed keepX values from earlier components:\n", flush=True)
            print(f"{_keep_x_to_dataframe(fixed_keep_x).to_string()}\n", flush=True)
        component_cache = {}

        round_number = 0
        while True:
            round_number += 1
            subgrids = _unseen_subgrids(grid, component_cache)
            print(f"Component {component}, round {round_number}\n", flush=True)
            print("================================\n", flush=True)
            print("Current keepX grid:", flush=True)
            print(f"{_grid_to_dataframe(grid).to_string()}\n", flush=True)
            proposed_combinations = prod(len(values) for values in grid.values())
            unseen_combinations = sum(
                prod(len(values) for values in subgrid.values()) for subgrid in subgrids
            )
            print(
                f"Proposed {proposed_combinations} keepX combinations; "
                f"evaluating {unseen_combinations} unseen combination(s) "
                f"in {len(subgrids)} subgrid(s).\n",
                flush=True,
            )
            if not subgrids:
                print(
                    "Every proposed combination is already cached; fixing "
                    "this component.\n",
                    flush=True,
                )
                break

            for subgrid in subgrids:
                if len(subgrids) > 1:
                    print("Evaluating unseen keepX subgrid:\n", flush=True)
                    print(f"{_grid_to_dataframe(subgrid).to_string()}\n", flush=True)
                previous_keepx = fixed_keep_x if component > 1 else None
                if round_runner is None:
                    tune_result = _run_tuning_round(
                        blocks,
                        target,
                        design,
                        component,
                        subgrid,
                        previous_keepx,
                        tol,
                        max_iter,
                        near_zero_var,
                        scale,
                        validation,
                        folds,
                        nrepeat,
                        signif_threshold,
                        distance,
                        measure,
                        weighted,
                        seed,
                        bpparam,
                    )
                    round_error_rates = _r_feature_selection_error_rate_to_dataframe(
                        tune_result
                    )
                else:
                    round_error_rates = round_runner(component, subgrid, previous_keepx)
                round_error_rates = round_error_rates.loc[
                    round_error_rates["component"] == component - 1
                ].copy()
                if round_error_rates.empty:
                    raise ValueError(
                        "mixOmics did not return error rates for the current "
                        f"component ({component})."
                    )
                _add_evaluations_to_cache(
                    component_cache, round_error_rates, tuple(blocks)
                )
            round_decisions, current_selection, refinement_anchors = (
                _select_near_optimal_keep_x(
                    _cache_to_error_rates(component_cache, component - 1),
                    tuple(blocks),
                    nrepeat,
                    selection_rule,
                    ber_margin,
                    se_multiplier,
                )
            )
            print(
                "Chosen sparse keepX values "
                f"(measure={measure}, distance={distance}; "
                f"rule={selection_rule}):",
                flush=True,
            )
            print(
                _keep_x_to_dataframe(
                    current_selection, component_start=component
                ).to_string()
                + "\n",
                flush=True,
            )
            threshold = round_decisions["threshold"].iloc[0]
            acceptable = round_decisions["within_plateau"].sum()
            best_decision = round_decisions.loc[round_decisions["mean"].idxmin()]
            print(
                f"Best mean BER={best_decision['mean']:.6g}, "
                f"SE={best_decision['standard_error']:.6g}; "
                f"near-optimal plateau: {acceptable} candidate(s), "
                f"BER threshold={threshold:.6g}.\n",
                flush=True,
            )

            next_grid = _refine_grids(
                grid,
                refinement_anchors,
                blocks,
                min_keepx,
                grid_size,
                refinement_factor,
            )
            if not _unseen_subgrids(next_grid, component_cache):
                print(
                    "The selected local grid contains only combinations "
                    "already evaluated; "
                    "fixing this component.\n",
                    flush=True,
                )
                break
            grid = next_grid

        evaluation_cache[component] = component_cache
        final_component_decisions[component] = round_decisions
        fixed_keep_x = {
            name: fixed_keep_x[name] + current_selection[name] for name in blocks
        }
        print(f"Fixed component {component} keepX values.\n", flush=True)

    _print_final_selection_summary(
        fixed_keep_x, final_component_decisions, se_multiplier
    )

    return AdaptiveKeepXResult(
        keep_x=fixed_keep_x,
        block_names=tuple(blocks),
        evaluation_cache=evaluation_cache,
    )


def _validate_min_keepx_against_blocks(blocks, min_keepx):
    """Ensures every input block has at least ``min_keepx`` features."""
    invalid_blocks = [
        str(name) for name, table in blocks.items() if table.shape[1] < min_keepx
    ]
    if invalid_blocks:
        raise ValueError(
            "min_keepx exceeds the available feature count for: "
            f"{', '.join(invalid_blocks)}."
        )


def _initial_grids(
    blocks, min_keepx, initial_fraction, grid_size
) -> dict[str, list[int]]:
    """Builds feature-count-aware first-round candidate grids."""
    grids = {}
    for name, table in blocks.items():
        initial_upper = min(
            table.shape[1],
            max(min_keepx, ceil(table.shape[1] * initial_fraction)),
        )
        grids[name] = _spaced_integers(
            min_keepx, initial_upper, grid_size, geometric=True
        )
    return grids


def _refine_grids(
    grid, selection, blocks, min_keepx, grid_size, factor
) -> dict[str, list[int]]:
    """Builds one bounded local candidate grid around each selected count."""
    refined = {}
    for name, candidates in grid.items():
        hard_upper = blocks[name].shape[1]
        centres = sorted(set(selection[name]))
        local_candidates = set(centres)
        for centre in centres:
            local_candidates.update(
                _local_candidates(
                    candidates, centre, min_keepx, hard_upper, grid_size, factor
                )
            )
        refined[name] = sorted(local_candidates)
    return refined


def _keepx_label(values: tuple[int, ...]) -> str:
    """Serialises one block-order-preserving keepX tuple for mixOmics."""
    return "_".join(map(str, values))


def _unseen_subgrids(
    grid: dict[str, list[int]], cache: dict[tuple[int, ...], dict[str, object]]
) -> list[dict[str, list[int]]]:
    """Partitions uncached grid tuples into disjoint rectangular subgrids.

    ``tune.block.splsda`` can only receive one Cartesian grid at a time. This
    greedy cover therefore groups as many unseen tuples as possible into each
    valid subgrid, so cached combinations are never sent to mixOmics again.
    """
    names = tuple(grid)
    candidates = tuple(tuple(grid[name]) for name in names)
    remaining = {
        values for values in cartesian_product(*candidates) if values not in cache
    }
    subgrids = []
    while remaining:
        seed = min(remaining)
        rectangle = [[value] for value in seed]
        changed = True
        while changed:
            changed = False
            for dimension, values in enumerate(candidates):
                for value in values:
                    if value in rectangle[dimension]:
                        continue
                    trial = [list(axis) for axis in rectangle]
                    trial[dimension].append(value)
                    if all(
                        tuple(point) in remaining for point in cartesian_product(*trial)
                    ):
                        rectangle[dimension].append(value)
                        changed = True
        rectangle_tuples = set(cartesian_product(*rectangle))
        remaining.difference_update(rectangle_tuples)
        subgrids.append(
            {name: sorted(values) for name, values in zip(names, rectangle)}
        )
    return subgrids


def _add_evaluations_to_cache(
    cache: dict[tuple[int, ...], dict[str, float | int]],
    error_rates: pd.DataFrame,
    block_names: tuple[str, ...],
) -> None:
    """Adds unique mean/SD tuning records to one component's cache."""
    summary = error_rates.loc[
        error_rates["statistic"].isin(["mean", "sd"]),
        ["keepx", "statistic", "value"],
    ].pivot(index="keepx", columns="statistic", values="value")
    if summary.empty or not {"mean", "sd"}.issubset(summary.columns):
        raise ValueError(
            "mixOmics must return mean and SD error rates for every unseen "
            "keepX combination."
        )
    for keep_x, values in summary.iterrows():
        keep_x = str(keep_x)
        keep_x_values = tuple(_split_keep_x(keep_x, len(block_names)))
        if keep_x_values in cache:
            raise ValueError(f"Duplicate keepX evaluation returned: {keep_x}.")
        mean, sd = float(values["mean"]), float(values["sd"])
        if not np.isfinite([mean, sd]).all() or sd < 0:
            raise ValueError(
                "mixOmics returned missing, non-finite, or negative error " "rates."
            )
        cache[keep_x_values] = {
            "mean": mean,
            "sd": sd,
        }


def _cache_to_error_rates(
    cache: dict[tuple[int, ...], dict[str, float | int]], component: int
) -> pd.DataFrame:
    """Converts a component cache to long-form records for selection."""
    records = []
    for keep_x_values, entry in cache.items():
        keep_x = _keepx_label(keep_x_values)
        records.extend(
            [
                {
                    "keepx": keep_x,
                    "component": component,
                    "statistic": "mean",
                    "value": entry["mean"],
                },
                {
                    "keepx": keep_x,
                    "component": component,
                    "statistic": "sd",
                    "value": entry["sd"],
                },
            ]
        )
    return pd.DataFrame(records)


def _select_near_optimal_keep_x(
    error_rates: pd.DataFrame,
    block_names: tuple[str, ...],
    nrepeat: int,
    selection_rule: str,
    ber_margin: float,
    se_multiplier: float = 1.0,
) -> tuple[pd.DataFrame, dict[str, list[int]], dict[str, list[int]]]:
    """Ranks BER-equivalent candidates and returns selection/refinement anchors.

    The input must contain mean and SD records for one component. The final
    selection is deliberately made in Python so that
    a plateau can favour a smaller, more interpretable DIABLO signature than
    mixOmics' numerical minimum.
    """
    expected = {"keepx", "statistic", "value"}
    missing = expected.difference(error_rates.columns)
    if missing:
        raise ValueError(
            "Tuning error rates are missing required columns: "
            f"{', '.join(sorted(missing))}."
        )
    summary = error_rates.loc[
        error_rates["statistic"].isin(["mean", "sd"]),
        ["keepx", "statistic", "value"],
    ].pivot(index="keepx", columns="statistic", values="value")
    if summary.empty or not {"mean", "sd"}.issubset(summary.columns):
        raise ValueError(
            "mixOmics must return finite mean and SD error rates for every "
            "tested keepX combination."
        )
    summary = summary.reset_index()
    if not np.isfinite(summary[["mean", "sd"]].to_numpy(dtype=float)).all():
        raise ValueError("mixOmics returned missing or non-finite mean/SD error rates.")
    if (summary["sd"] < 0).any():
        raise ValueError("mixOmics returned a negative error-rate SD.")

    parsed = summary["keepx"].apply(
        lambda keep_x: _split_keep_x(keep_x, len(block_names))
    )
    value_columns = [f"keepx:{name}" for name in block_names]
    summary[value_columns] = pd.DataFrame(parsed.tolist(), index=summary.index)
    summary["standard_error"] = summary["sd"] / sqrt(nrepeat)
    minimum = summary.loc[summary["mean"].idxmin()]
    threshold = minimum["mean"] + (
        se_multiplier * minimum["standard_error"]
        if selection_rule == "one_se"
        else ber_margin
    )
    summary["threshold"] = threshold
    summary["ber_delta"] = summary["mean"] - minimum["mean"]
    summary["within_plateau"] = summary["mean"] <= threshold
    summary["total_keepx"] = summary[value_columns].sum(axis=1)

    plateau = summary.loc[summary["within_plateau"]].sort_values(
        ["total_keepx", "mean", *value_columns],
        kind="stable",
    )
    summary["selection_rank"] = pd.Series(pd.NA, index=summary.index, dtype="Int64")
    summary.loc[plateau.index, "selection_rank"] = range(1, len(plateau) + 1)
    selected_index = plateau.index[0]
    summary["selected"] = summary.index == selected_index
    anchor_indices = [selected_index]
    summary["refinement_anchor"] = summary.index.isin(anchor_indices)

    selected_values = summary.loc[selected_index, value_columns].astype(int).tolist()
    selected = dict(zip(block_names, ([value] for value in selected_values)))
    anchors = {
        name: sorted(set(summary.loc[anchor_indices, column].astype(int).tolist()))
        for name, column in zip(block_names, value_columns)
    }
    return summary, selected, anchors


def _local_candidates(candidates, centre, lower_bound, upper_bound, grid_size, factor):
    """Produces a narrower interior interval or an outward edge interval."""
    position = candidates.index(centre)
    left_gap = (
        centre - candidates[position - 1]
        if position > 0
        else candidates[1] - centre if len(candidates) > 1 else 1
    )
    right_gap = (
        candidates[position + 1] - centre
        if position < len(candidates) - 1
        else centre - candidates[position - 1] if position > 0 else 1
    )
    inward_left = max(1, floor(left_gap / factor))
    inward_right = max(1, floor(right_gap / factor))
    outward_left = ceil(left_gap * factor)
    outward_right = ceil(right_gap * factor)
    if position == 0:
        lower = max(lower_bound, centre - outward_left)
        upper = min(upper_bound, centre + inward_right)
    elif position == len(candidates) - 1:
        lower = max(lower_bound, centre - inward_left)
        upper = min(upper_bound, centre + outward_right)
    else:
        lower = max(lower_bound, centre - inward_left)
        upper = min(upper_bound, centre + inward_right)
    return _spaced_integers(lower, upper, grid_size, geometric=False)


def _spaced_integers(lower: int, upper: int, size: int, geometric: bool) -> list[int]:
    """Creates unique bounded integer candidates with geometric or local spacing."""
    if lower == upper:
        return [lower]
    values = (
        np.geomspace(lower, upper, num=size)
        if geometric
        else np.linspace(lower, upper, num=size)
    )
    return sorted({int(round(value)) for value in values} | {lower, upper})


def _has_new_candidates(current_grid, next_grid) -> bool:
    """Returns whether refinement adds any untested per-block candidate value."""
    return any(
        not set(next_grid[name]).issubset(current_grid[name]) for name in current_grid
    )


def _run_tuning_round(
    blocks,
    target,
    design,
    ncomp,
    keep_x,
    already_tested_x,
    tol,
    max_iter,
    near_zero_var,
    scale,
    validation,
    folds,
    nrepeat,
    signif_threshold,
    distance,
    measure,
    weighted,
    seed,
    bpparam,
):
    """Runs one current-component mixOmics tuning round.

    ``already_tested_x`` fixes every preceding component, allowing mixOmics to
    evaluate only the new component represented by ``ncomp``.
    """
    r_blocks, r_target, r_design = _to_r_inputs(blocks, target, design)
    r_keep_x = ListVector({name: IntVector(values) for name, values in keep_x.items()})
    parameters = {
        "ncomp": ncomp,
        "tol": tol,
        "max.iter": max_iter,
        "near.zero.var": near_zero_var,
        "design": r_design,
        "scale": scale,
        "test.keepX": r_keep_x,
        "validation": validation,
        "folds": folds,
        "nrepeat": nrepeat,
        "signif.threshold": signif_threshold,
        "dist": distance,
        "measure": measure,
        "weighted": weighted,
        "progressBar": False,
        "light.output": True,
        "BPPARAM": bpparam,
        "seed": seed,
    }
    if already_tested_x:
        parameters["already.tested.X"] = ListVector(
            {name: IntVector(values) for name, values in already_tested_x.items()}
        )
    return _quiet_tune_block_splsda(
        r_blocks,
        r_target,
        **parameters,
    )


def _selected_keep_x(tune_result) -> dict[str, list[int]]:
    """Converts mixOmics' component-wise ``choice.keepX`` to Python values."""
    values = tune_result.rx2("choice.keepX")
    return {
        str(name): [int(value) for value in block_values]
        for name, block_values in zip(values.names, values)
    }


def _component_selection(
    selection: dict[str, list[int]], component: int
) -> dict[str, list[int]]:
    """Extracts the one newly tuned component from mixOmics' full selection."""
    try:
        return {name: [values[component - 1]] for name, values in selection.items()}
    except IndexError as error:
        raise ValueError(
            "mixOmics did not return a keepX choice for the current component."
        ) from error


def _grid_to_dataframe(grid: dict[str, list[int]]) -> pd.DataFrame:
    """Formats ragged candidate grids for readable console output."""
    return pd.DataFrame(
        {
            "block": list(grid),
            "keepX candidates": [
                ", ".join(map(str, values)) for values in grid.values()
            ],
        }
    ).set_index("block")


def _keep_x_to_dataframe(
    keep_x: dict[str, list[int]], component_start: int = 1
) -> pd.DataFrame:
    """Formats selected component-wise counts for readable console output."""
    table = pd.DataFrame(keep_x)
    table.index = [
        f"component {component}"
        for component in range(component_start, component_start + len(table))
    ]
    return table


def _print_final_selection_summary(
    keep_x: dict[str, list[int]],
    component_decisions: dict[int, pd.DataFrame],
    se_multiplier: float,
) -> None:
    """Prints final selections and marginal one-SE plateau ranges by block."""
    print("Final adaptive keepX selection:\n", flush=True)
    print(f"{_keep_x_to_dataframe(keep_x).to_string()}\n", flush=True)
    for component, decisions in component_decisions.items():
        plateau = decisions.loc[decisions["within_plateau"]]
        threshold = decisions["threshold"].iloc[0]
        best = decisions.loc[decisions["mean"].idxmin()]
        print(
            f"\nComponent {component}: {len(plateau)} candidate(s) within "
            f"the selection threshold (best mean BER={best['mean']:.6g}, "
            f"SE={best['standard_error']:.6g}, threshold={threshold:.6g}).\n",
            flush=True,
        )
        print(
            _selection_comparison_to_dataframe(decisions, se_multiplier).to_string()
            + "\n",
            flush=True,
        )


def _selection_comparison_to_dataframe(
    decisions: pd.DataFrame, se_multiplier: float
) -> pd.DataFrame:
    """Formats the numerical best and sparse models up to the SE allowance."""
    best = decisions.loc[decisions["mean"].idxmin()]
    keepx_columns = [
        column for column in best.index if str(column).startswith("keepx:")
    ]
    records = []
    candidates = [("lowest mean BER", best, 0)]
    whole_multipliers = range(1, int(se_multiplier) + 1)
    multipliers = [float(multiplier) for multiplier in whole_multipliers]
    if se_multiplier not in multipliers:
        multipliers.append(se_multiplier)
    for multiplier in multipliers:
        threshold = best["mean"] + multiplier * best["standard_error"]
        eligible = decisions.loc[decisions["mean"] <= threshold].sort_values(
            ["total_keepx", "mean", *keepx_columns],
            kind="stable",
        )
        candidates.append(
            (f"sparsest within {multiplier:g} SE", eligible.iloc[0], multiplier)
        )
    for label, candidate, multiplier in candidates:
        record = {
            "model": label,
            "mean BER": candidate["mean"],
            "SD": candidate["sd"],
            "SE": candidate["standard_error"],
            "BER above best": candidate["mean"] - best["mean"],
            "SE allowance": multiplier,
        }
        record.update(
            {
                column.removeprefix("keepx:"): int(candidate[column])
                for column in keepx_columns
            }
        )
        records.append(record)
    return pd.DataFrame(records).set_index("model")


def _split_keep_x(keep_x: str, expected_blocks: int) -> list[int]:
    """Parses mixOmics' underscore-separated keepX-combination row label."""
    values = [int(value) for value in str(keep_x).split("_")]
    if len(values) != expected_blocks:
        raise ValueError(
            "The tuning error-rate table does not match the expected number "
            "of input blocks."
        )
    return values
