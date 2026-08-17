# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
"""QIIME-facing DIABLO component-selection action."""
import secrets

import numpy as np
import pandas as pd
from rachis import CategoricalMetadataColumn, Metadata
from rachis.plugin import CaptureHolder
from rpy2.robjects import r

from q2_mfa.pls.types._tune_components_result import _PLSTuneComponentsResult
from q2_mfa.pls.utils import (
    _align_samples,
    _build_bpparam,
    _r_vote_error_rate_to_dataframe,
    _resolve_design,
    _to_r_inputs,
)


def tune_components_block_splsda(
    tables: pd.DataFrame,
    y: CategoricalMetadataColumn,
    design_matrix: Metadata = None,
    design_weight: float | None = None,
    ncomp: int = 2,
    scale: bool = True,
    tol: float = 1e-6,
    max_iter: int = 100,
    near_zero_var: bool = False,
    validation: str = "Mfold",
    folds: int = 10,
    nrepeat: int = 3,
    signif_threshold: float = 0.01,
    seed: CaptureHolder[int] = None,
    threads: int = 1,
) -> _PLSTuneComponentsResult:
    """Selects DIABLO components with weighted and majority voting."""
    r("suppressPackageStartupMessages(library(mixOmics))")
    blocks, target = _align_samples(tables, y)
    design = _resolve_design(design_matrix, design_weight, list(blocks))
    resolved_seed = CaptureHolder.get_or_set(seed, lambda: secrets.randbelow(2**31))
    bpparam = _build_bpparam(threads, resolved_seed)
    r_blocks, r_target, r_design = _to_r_inputs(blocks, target, design)

    print("Evaluate number of components (ncomp)\n", flush=True)
    perf_model = r["block.plsda"](
        r_blocks,
        r_target,
        **{
            "ncomp": ncomp,
            "design": r_design,
            "scale": scale,
            "tol": tol,
            "max.iter": max_iter,
            "near.zero.var": near_zero_var,
        },
    )
    perf_result = r["perf"](
        perf_model,
        **{
            "dist": "all",
            "validation": validation,
            "folds": folds,
            "nrepeat": nrepeat,
            "signif.threshold": signif_threshold,
            "BPPARAM": bpparam,
            "seed": resolved_seed,
            "progressBar": False,
        },
    )
    frameworks = ("WeightedVote", "MajorityVote")
    choice_matrix = pd.concat(
        [
            _choice_matrix_to_dataframe(perf_result, framework)
            for framework in frameworks
        ],
        ignore_index=True,
    )
    for framework in frameworks:
        _print_component_choice(
            choice_matrix.loc[
                choice_matrix["vote"] == framework.removesuffix("Vote").lower()
            ],
            framework,
        )
    return _PLSTuneComponentsResult(
        error_rate=pd.concat(
            [
                _r_vote_error_rate_to_dataframe(perf_result, framework)
                for framework in frameworks
            ],
            ignore_index=True,
        ),
        choice_matrix=choice_matrix,
    )


def _choice_matrix_to_dataframe(perf_result, vote: str) -> pd.DataFrame:
    """Converts one mixOmics component-choice matrix to long-form records."""
    matrix = perf_result.rx2("choice.ncomp").rx2(vote)
    columns = ["vote", "measure", "distance", "ncomp"]
    if type(matrix).__name__ == "NULLType":
        return pd.DataFrame(columns=columns)
    values = np.asarray(matrix)
    records = [
        {
            "vote": vote.removesuffix("Vote").lower(),
            "measure": str(measure),
            "distance": str(distance),
            "ncomp": int(value),
        }
        for measure, row in zip(r["rownames"](matrix), values)
        for distance, value in zip(r["colnames"](matrix), row)
        if not pd.isna(value)
    ]
    return pd.DataFrame(records, columns=columns)


def _print_component_choice(choice_table: pd.DataFrame, vote: str) -> None:
    """Prints one mixOmics vote framework's component-choice matrix."""
    if choice_table.empty:
        print(f"{vote} component-choice matrix is unavailable.\n", flush=True)
        return
    choice_table = choice_table.pivot(
        index="measure", columns="distance", values="ncomp"
    )
    print(f"{vote} component-choice matrix:\n", flush=True)
    print(f"{choice_table.to_string()}\n", flush=True)
