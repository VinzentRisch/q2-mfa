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
from typing import Generator, Literal

import numpy as np
import pandas as pd

from q2_mfa.pls.feature_selection_block_splsda import _parse_keepx_collection


@dataclass(frozen=True)
class AdaptiveKeepXResult:
    """Selected counts and tuning results from adaptive grid refinement.

    Attributes:
        keep_x: Selected retained-feature counts by block and component.
        block_names: Input-block names in the order used by mixOmics.
        error_rates: All unique component-wise keepX evaluations in the normal
            wide feature-selection error-rate format.
    """

    keep_x: dict[str, list[int]]
    block_names: tuple[str, ...]
    error_rates: pd.DataFrame


@dataclass(frozen=True)
class GridRequest:
    """One registered feature-selection action invocation requested by tuning."""

    component: int
    keepx: dict[str, list[int]] | None
    already_tested_keepx: dict[str, list[int]] | None


def adaptive_keepx_refinement(
    block_feature_counts: dict[str, int],
    ncomp: int,
    *,
    initial_keepx=None,
    min_keepx: int = 5,
    max_keepx_fraction: float = 0.2,
    grid_size: int = 5,
    parallel_subgrids: int = 1,
    refinement_factor: float = 2.0,
    selection_rule: Literal["one_se", "absolute_margin"] = "one_se",
    nrepeat: int = 3,
) -> Generator[tuple[GridRequest, ...], tuple[pd.DataFrame, ...], AdaptiveKeepXResult]:
    """Tunes DIABLO ``keepX`` with a coarse-to-fine adaptive grid.

    Components are tuned sequentially. Each component receives its own
    coarse-to-fine grid; once all of its refinement rounds are complete, its
    selected counts are supplied through mixOmics' ``already.tested.X`` while
    the next component is tuned. Each round narrows around the numerical
    minimum-BER combination from the full component cache. Once refinement
    is complete, the selection rule chooses the final retained-feature counts.
    If an anchor lies on a grid edge, the next grid expands in that direction,
    but never beyond the number of features in its block.

    ``grid_size`` controls the initial candidate count per block and the
    number of local candidates around each selected component value in later
    rounds. A refinement grid can therefore contain more than ``grid_size``
    values when components select different values.

    Args:
        block_feature_counts: Available feature count for each named input
            block. The strategy uses these bounds to construct valid grids.
        ncomp: Number of components to tune.
        initial_keepx: Optional QIIME keepX collection used as the first grid
            for every component. When supplied, automatic first-grid
            construction settings are ignored.
        min_keepx: Smallest retained-feature count considered during refinement.
        max_keepx_fraction: Initial upper-bound fraction per block.
        grid_size: Initial and per-component local candidate count.
        parallel_subgrids: Desired number of zero-repeat action subgrids in
            each refinement round. More subgrids may be required when cached
            combinations leave holes in the proposed grid.
        refinement_factor: Finite factor greater than one used to shrink
            interior local intervals and expand intervals at a grid edge.
        selection_rule: ``one_se`` selects candidates within one standard
            error of minimum BER; ``absolute_margin`` selects only the
            numerical minimum BER.
        nrepeat: Cross-validation repeats.
        Yields: Tuples of grid requests that the pipeline executes through
            the registered private feature-selection action. Each resumed
            value must be the matching tuple of wide mean/SD error-rate
            tables.

    Returns:
        AdaptiveKeepXResult: Final component-wise counts and the unique
            component-wise evaluation cache.

    Raises:
        ValueError: If a grid is too large or refinement settings cannot retain
            every component value.
    """
    _validate_min_keepx_against_feature_counts(
        block_feature_counts,
        min_keepx,
    )
    initial_keepx = (
        _parse_keepx_collection(
            dict(getattr(initial_keepx, "collection", initial_keepx)),
            list(block_feature_counts),
            ncomp,
        )
        if initial_keepx is not None
        else None
    )

    block_names = tuple(block_feature_counts)
    keepx_columns = [f"keepx_{name}" for name in block_names]
    error_rate_columns = [*keepx_columns, "component", "mean", "sd"]
    error_rates = pd.DataFrame(
        {
            **{column: pd.Series(dtype="Int64") for column in keepx_columns},
            "component": pd.Series(dtype="Int64"),
            "mean": pd.Series(dtype="float64"),
            "sd": pd.Series(dtype="float64"),
        }
    )
    fixed_keep_x = {name: [] for name in block_feature_counts}

    print("Sequential adaptive keepX grid refinement\n", flush=True)
    for component in range(1, ncomp + 1):
        grid = (
            {name: values.copy() for name, values in initial_keepx.items()}
            if initial_keepx is not None
            else _initial_grids(
                block_feature_counts,
                min_keepx,
                max_keepx_fraction,
                grid_size,
            )
        )
        print(f"Tune component {component} of {ncomp}\n", flush=True)
        if component > 1:
            print("Fixed keepX values from earlier components:\n", flush=True)
            print(f"{_keep_x_to_dataframe(fixed_keep_x).to_string()}\n", flush=True)
        round_number = 0
        while True:
            round_number += 1
            component_cache = error_rates.loc[error_rates["component"] == component]
            subgrids = _unseen_subgrids(
                grid,
                component_cache,
                block_names,
                parallel_subgrids,
            )
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

            previous_keepx = fixed_keep_x if component > 1 else None
            requests = []
            for subgrid in subgrids:
                if len(subgrids) > 1:
                    print("Evaluating unseen keepX subgrid:\n", flush=True)
                    print(f"{_grid_to_dataframe(subgrid).to_string()}\n", flush=True)
                requests.append(
                    GridRequest(
                        component=component,
                        keepx=subgrid,
                        already_tested_keepx=previous_keepx,
                    )
                )
            round_error_rate_tables = yield tuple(requests)
            for round_error_rates in round_error_rate_tables:
                round_error_rates = round_error_rates.loc[
                    round_error_rates["component"] == component
                ].copy()
                if round_error_rates.empty:
                    raise ValueError(
                        "mixOmics did not return error rates for the current "
                        f"component ({component})."
                    )
                error_rates = pd.concat(
                    [error_rates, round_error_rates[error_rate_columns]],
                    ignore_index=True,
                )
            refinement_anchor = _select_near_optimal_keep_x(
                error_rates.loc[error_rates["component"] == component],
                block_names,
                nrepeat,
                "absolute_margin",
            )
            print(
                "Lowest-BER keepX values used for refinement:",
                flush=True,
            )
            print(
                _keep_x_to_dataframe(
                    refinement_anchor, component_start=component
                ).to_string()
                + "\n",
                flush=True,
            )
            next_grid = _refine_grids(
                grid,
                refinement_anchor,
                block_feature_counts,
                min_keepx,
                grid_size,
                refinement_factor,
            )
            component_cache = error_rates.loc[error_rates["component"] == component]
            if not _unseen_subgrids(next_grid, component_cache, block_names):
                print(
                    "The selected local grid contains only combinations "
                    "already evaluated; "
                    "fixing this component.\n",
                    flush=True,
                )
                break
            grid = next_grid

        current_selection = _select_near_optimal_keep_x(
            error_rates.loc[error_rates["component"] == component],
            block_names,
            nrepeat,
            selection_rule,
        )
        print(
            "Final selected keepX values " f"(rule={selection_rule}):",
            flush=True,
        )
        print(
            _keep_x_to_dataframe(
                current_selection, component_start=component
            ).to_string()
            + "\n",
            flush=True,
        )
        fixed_keep_x = {
            name: fixed_keep_x[name] + current_selection[name]
            for name in block_feature_counts
        }
        print(f"Fixed component {component} keepX values.\n", flush=True)

    _print_final_selection_summary(fixed_keep_x)

    return AdaptiveKeepXResult(
        keep_x=fixed_keep_x,
        block_names=block_names,
        error_rates=error_rates,
    )


def _validate_min_keepx_against_feature_counts(block_feature_counts, min_keepx):
    """Ensures every input block has at least ``min_keepx`` features."""
    invalid_blocks = [
        str(name)
        for name, feature_count in block_feature_counts.items()
        if feature_count < min_keepx
    ]
    if invalid_blocks:
        raise ValueError(
            "min_keepx exceeds the available feature count for: "
            f"{', '.join(invalid_blocks)}."
        )


def _initial_grids(
    block_feature_counts, min_keepx, initial_fraction, grid_size
) -> dict[str, list[int]]:
    """Builds feature-count-aware first-round candidate grids."""
    grids = {}
    for name, feature_count in block_feature_counts.items():
        initial_upper = min(
            feature_count,
            max(min_keepx, ceil(feature_count * initial_fraction)),
        )
        grids[name] = _spaced_integers(
            min_keepx, initial_upper, grid_size, geometric=True
        )
    return grids


def _refine_grids(
    grid, selection, block_feature_counts, min_keepx, grid_size, factor
) -> dict[str, list[int]]:
    """Builds one bounded local candidate grid around each selected count."""
    refined = {}
    for name, candidates in grid.items():
        hard_upper = block_feature_counts[name]
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


def _unseen_subgrids(
    grid: dict[str, list[int]],
    error_rates: pd.DataFrame,
    block_names: tuple[str, ...],
    parallel_subgrids: int = 1,
) -> list[dict[str, list[int]]]:
    """Partitions uncached tuples into balanced, disjoint rectangular grids.

    ``tune.block.splsda`` can only receive one Cartesian grid at a time. This
    The zero-repeat greedy cover groups unseen tuples into valid subgrids,
    then splits large rectangles to approach the requested parallelism.
    Cached combinations are never sent to mixOmics.
    """
    names = tuple(grid)
    candidates = tuple(tuple(grid[name]) for name in names)
    keepx_columns = [f"keepx_{name}" for name in block_names]
    seen = set(error_rates[keepx_columns].itertuples(index=False, name=None))
    remaining = {
        values for values in cartesian_product(*candidates) if values not in seen
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
    return _split_subgrids(subgrids, names, parallel_subgrids)


def _split_subgrids(
    subgrids: list[dict[str, list[int]]], names: tuple[str, ...], target: int
) -> list[dict[str, list[int]]]:
    """Splits the largest rectangles until reaching the requested target."""
    subgrids = _sort_subgrids(subgrids, names)
    while len(subgrids) < target:
        splittable = [
            (index, subgrid)
            for index, subgrid in enumerate(subgrids)
            if _subgrid_size(subgrid) > 1
        ]
        if not splittable:
            break
        index, subgrid = max(
            splittable,
            key=lambda candidate: (_subgrid_size(candidate[1]), -candidate[0]),
        )
        left, right = _split_subgrid(subgrid, names)
        subgrids[index : index + 1] = [left, right]
        subgrids = _sort_subgrids(subgrids, names)
    return subgrids


def _split_subgrid(
    subgrid: dict[str, list[int]], names: tuple[str, ...]
) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    """Bisects a subgrid along the axis with the most balanced child sizes."""
    split_candidates = []
    for dimension, name in enumerate(names):
        values = subgrid[name]
        other_size = prod(len(subgrid[other]) for other in names if other != name)
        for split_index in range(1, len(values)):
            left_size = split_index * other_size
            right_size = (len(values) - split_index) * other_size
            split_candidates.append(
                (
                    abs(left_size - right_size),
                    dimension,
                    split_index,
                )
            )
    _, dimension, split_index = min(split_candidates)
    name = names[dimension]
    left = {block: values.copy() for block, values in subgrid.items()}
    right = {block: values.copy() for block, values in subgrid.items()}
    left[name] = subgrid[name][:split_index]
    right[name] = subgrid[name][split_index:]
    return left, right


def _subgrid_size(subgrid: dict[str, list[int]]) -> int:
    """Returns the number of Cartesian keepX combinations in one subgrid."""
    return prod(len(values) for values in subgrid.values())


def _sort_subgrids(
    subgrids: list[dict[str, list[int]]], names: tuple[str, ...]
) -> list[dict[str, list[int]]]:
    """Orders subgrids by their block-order-preserving candidate values."""
    return sorted(subgrids, key=lambda subgrid: tuple(subgrid[name] for name in names))


def _select_near_optimal_keep_x(
    error_rates: pd.DataFrame,
    block_names: tuple[str, ...],
    nrepeat: int,
    selection_rule: str,
) -> dict[str, list[int]]:
    """Ranks BER-equivalent candidates and returns the selected keepX values.

    The input must contain mean and SD records for one component. The final
    selection is deliberately made in Python so that
    a plateau can favour a smaller, more interpretable DIABLO signature than
    mixOmics' numerical minimum.
    """
    keepx_columns = [f"keepx_{name}" for name in block_names]
    minimum = error_rates.loc[error_rates["mean"].idxmin()]
    threshold = minimum["mean"] + (
        minimum["sd"] / sqrt(nrepeat) if selection_rule == "one_se" else 0
    )
    acceptable = error_rates.loc[error_rates["mean"] <= threshold]
    selected_index = (
        acceptable.assign(_total_keepx=acceptable[keepx_columns].sum(axis=1))
        .sort_values(
            ["_total_keepx", "mean", *keepx_columns],
            kind="stable",
        )
        .index[0]
    )
    selected_values = (
        error_rates.loc[selected_index, keepx_columns].astype(int).tolist()
    )
    selected = dict(zip(block_names, ([value] for value in selected_values)))
    return selected


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
    """Creates unique bounded integer candidates with selected spacing."""
    if lower == upper:
        return [lower]
    values = (
        np.geomspace(lower, upper, num=size)
        if geometric
        else np.linspace(lower, upper, num=size)
    )
    return sorted({int(round(value)) for value in values} | {lower, upper})


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


def _print_final_selection_summary(keep_x: dict[str, list[int]]) -> None:
    """Prints the final selected keepX values for every component."""
    print("Final adaptive keepX selection:\n", flush=True)
    print(f"{_keep_x_to_dataframe(keep_x).to_string()}\n", flush=True)
