# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import secrets

import numpy as np
import pandas as pd
from q2templates.reports import matryoshka_template
from rachis import CategoricalMetadataColumn, Metadata
from rachis.plugin import CaptureHolder
from rpy2.robjects import r

from q2_mfa.pls.jsonl_descriptions import jsonl_descriptions
from q2_mfa.pls.types._format import PLSTuneComponentsDirFmt
from q2_mfa.pls.utils import (
    _align_samples,
    _build_bpparam,
    _r_vote_error_rate_to_dataframe,
    _resolve_design,
    _to_r_inputs,
)


def _tune_components_block_splsda(
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
) -> PLSTuneComponentsDirFmt:
    """Selects block PLS-DA components with weighted and majority voting."""
    r("suppressPackageStartupMessages(library(mixOmics))")
    blocks, target = _align_samples(dict(tables.collection), y.to_series())
    design = _resolve_design(design_matrix, design_weight, list(blocks))
    resolved_seed = CaptureHolder.get_or_set(seed, lambda: secrets.randbelow(2**31))
    bpparam = _build_bpparam(threads, resolved_seed)
    r_blocks, r_target, r_design = _to_r_inputs(blocks, target, design)

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
    weighted_choice_matrix = _choice_matrix_to_dataframe(perf_result, "WeightedVote")
    majority_choice_matrix = _choice_matrix_to_dataframe(perf_result, "MajorityVote")
    weighted_error_rate = _r_vote_error_rate_to_dataframe(perf_result, "WeightedVote")
    majority_error_rate = _r_vote_error_rate_to_dataframe(perf_result, "MajorityVote")
    _print_component_choice(weighted_choice_matrix, "WeightedVote")
    _print_component_choice(majority_choice_matrix, "MajorityVote")
    return _serialize_tune_components(
        weighted_error_rate,
        majority_error_rate,
        weighted_choice_matrix,
        majority_choice_matrix,
    )


def tune_components_block_splsda(
    ctx,
    tables,
    y,
    design_matrix=None,
    design_weight=None,
    ncomp=2,
    scale=True,
    tol=1e-6,
    max_iter=100,
    near_zero_var=False,
    validation="Mfold",
    folds=10,
    nrepeat=3,
    signif_threshold=0.01,
    seed=None,
    threads=1,
):
    """Tune block PLS-DA components and report selection diagnostics."""
    tune_components = ctx.get_action("mfa", "_tune_components_block_splsda")
    lineplot = ctx.get_action("vizard", "lineplot")
    tabulate = ctx.get_action("metadata", "tabulate")

    (tuning,) = tune_components(
        tables=tables,
        y=y,
        design_matrix=design_matrix,
        design_weight=design_weight,
        ncomp=ncomp,
        scale=scale,
        tol=tol,
        max_iter=max_iter,
        near_zero_var=near_zero_var,
        validation=validation,
        folds=folds,
        nrepeat=nrepeat,
        signif_threshold=signif_threshold,
        seed=seed,
        threads=threads,
    )
    tuning_data = tuning.view(PLSTuneComponentsDirFmt)

    weighted_error_rates = _error_rate_metadata(
        tuning_data.error_rate_weighted.view(Metadata)
    )
    majority_error_rates = _error_rate_metadata(
        tuning_data.error_rate_majority.view(Metadata)
    )
    (weighted_error_rate_plot,) = lineplot(
        metadata=weighted_error_rates,
        x_measure="component",
        y_measure="mean",
        replicate_method="none",
        group_by="error_rate",
        title="PLS-DA weighted-vote error rates",
    )
    (majority_error_rate_plot,) = lineplot(
        metadata=majority_error_rates,
        x_measure="component",
        y_measure="mean",
        replicate_method="none",
        group_by="error_rate",
        title="PLS-DA majority-vote error rates",
    )
    (weighted_choice_matrix,) = tabulate(
        input=tuning_data.choice_matrix_weighted.view(Metadata)
    )
    (majority_choice_matrix,) = tabulate(
        input=tuning_data.choice_matrix_majority.view(Metadata)
    )

    error_rate_report = ctx.make_report(
        matryoshka_template,
        {
            "Weighted vote": weighted_error_rate_plot,
            "Majority vote": majority_error_rate_plot,
        },
    )
    choice_matrix_report = ctx.make_report(
        matryoshka_template,
        {
            "Weighted vote": weighted_choice_matrix,
            "Majority vote": majority_choice_matrix,
        },
    )
    report = ctx.make_report(
        matryoshka_template,
        {
            "Error rates": error_rate_report,
            "Component choices": choice_matrix_report,
        },
    )
    return tuning, report


def _error_rate_metadata(error_rates: Metadata) -> Metadata:
    """Filters and labels overall error rates for component plotting."""
    error_rates = error_rates.to_dataframe().copy()
    error_rates = error_rates.loc[
        error_rates["class"].isin({"Overall.BER", "Overall.ER"})
    ]
    error_rates["error_rate"] = (
        error_rates["distance"].astype(str) + ": " + error_rates["class"].astype(str)
    )
    return Metadata(error_rates)


def _choice_matrix_to_dataframe(perf_result, vote: str) -> pd.DataFrame:
    """Converts one mixOmics component-choice matrix to a DataFrame."""
    matrix = perf_result.rx2("choice.ncomp").rx2(vote)
    if type(matrix).__name__ == "NULLType":
        return pd.DataFrame()
    values = np.asarray(matrix)
    return pd.DataFrame(
        values,
        index=pd.Index(r["rownames"](matrix), name="id"),
        columns=r["colnames"](matrix),
    )


def _print_component_choice(choice_table: pd.DataFrame, vote: str) -> None:
    """Prints one mixOmics vote's component-choice matrix."""
    if choice_table.empty:
        print(f"{vote} component-choice matrix is unavailable.\n", flush=True)
        return
    print(f"{vote} component-choice matrix:\n", flush=True)
    print(f"{choice_table.to_string()}\n", flush=True)


def _serialize_tune_components(
    error_rate_weighted: pd.DataFrame,
    error_rate_majority: pd.DataFrame,
    choice_matrix_weighted: pd.DataFrame,
    choice_matrix_majority: pd.DataFrame,
) -> PLSTuneComponentsDirFmt:
    """Serializes component-tuning tables as Table JSONL files."""
    directory_format = PLSTuneComponentsDirFmt()
    error_rate_weighted = error_rate_weighted.copy()
    error_rate_majority = error_rate_majority.copy()
    choice_matrix_weighted = choice_matrix_weighted.reset_index()
    choice_matrix_majority = choice_matrix_majority.reset_index()

    error_rate_weighted.insert(
        0, "id", [f"row{index}" for index in range(1, len(error_rate_weighted) + 1)]
    )
    error_rate_majority.insert(
        0, "id", [f"row{index}" for index in range(1, len(error_rate_majority) + 1)]
    )

    error_rate_weighted.attrs["description"] = jsonl_descriptions["error_rate_weighted"]
    error_rate_majority.attrs["description"] = jsonl_descriptions["error_rate_majority"]
    choice_matrix_weighted.attrs["description"] = jsonl_descriptions[
        "choice_matrix_weighted"
    ]
    choice_matrix_majority.attrs["description"] = jsonl_descriptions[
        "choice_matrix_majority"
    ]

    directory_format.error_rate_weighted.write_data(error_rate_weighted, pd.DataFrame)
    directory_format.error_rate_majority.write_data(error_rate_majority, pd.DataFrame)
    directory_format.choice_matrix_weighted.write_data(
        choice_matrix_weighted, pd.DataFrame
    )
    directory_format.choice_matrix_majority.write_data(
        choice_matrix_majority, pd.DataFrame
    )
    return directory_format
