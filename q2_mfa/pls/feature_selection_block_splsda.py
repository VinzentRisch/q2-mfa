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
from rpy2.robjects import IntVector, ListVector, r
from rpy2.robjects.vectors import FactorVector

from q2_mfa.pls.auto_keepx import _cache_to_error_rates, adaptive_keepx_refinement
from q2_mfa.pls.jsonl_descriptions import jsonl_descriptions
from q2_mfa.pls.types._format import PLSFeatureSelectionDirFmt
from q2_mfa.pls.types._type import PLSFeatureSelection
from q2_mfa.pls.utils import (
    _build_bpparam,
    _resolve_design,
    _resolve_ncomp,
    _to_r_inputs,
)


def _feature_selection_block_splsda(
    tables: pd.DataFrame,
    y: CategoricalMetadataColumn,
    keepx: dict,
    already_tested_keepx: dict | None = None,
    design_matrix: Metadata = None,
    design_weight: float | None = None,
    ncomp: int = None,
    scale: bool = True,
    tol: float = 1e-6,
    max_iter: int = 100,
    near_zero_var: bool = False,
    validation: str = "Mfold",
    folds: int = 10,
    nrepeat: int = 3,
    signif_threshold: float = 0.01,
    distance: str = "max.dist",
    measure: str = "BER",
    weighted: bool = True,
    seed: int = None,
    threads: int = 1,
) -> PLSFeatureSelectionDirFmt:
    """
    Tunes block sPLS-DA (DIABLO) sparse feature counts with mixOmics.

    Consumes pre-aligned input blocks and categorical response, evaluates the
    supplied manual keepX candidate grid, and serializes error rates and the
    selected sparse-feature counts.

    Args:
        tables (ResultCollection): Named feature-table artifacts used as
            DIABLO blocks.
        y (CategoricalMetadataColumn): Categorical response labels for the
            samples.
        keepx (dict): Named comma-separated keepX candidate counts for each
            input block.
        design_matrix (Metadata, optional): Explicit block-relationship design
            matrix.
        design_weight (float, optional): Shared off-diagonal relationship
            weight used when no design matrix is supplied.
        ncomp (int): Resolved number of components to tune.
        scale (bool): Whether to standardize features within every block.
        tol (float): Convergence tolerance for the iterative model fit.
        max_iter (int): Maximum iterations for each model fit.
        near_zero_var (bool): Whether to remove zero or near-zero variance
            predictors before fitting.
        validation (str): Cross-validation strategy accepted by mixOmics.
        folds (int): Number of folds used for M-fold cross-validation.
        nrepeat (int): Number of cross-validation repetitions.
        signif_threshold (float): Minimum error-rate improvement required to
            retain an additional component.
        distance (str): Prediction distance used for classification.
        measure (str): Classification error measure used to select keepX.
        weighted (bool): Whether to use weighted rather than majority voting.
        seed (int): Random seed used for reproducible cross-validation.
        threads (int): Number of BiocParallel workers to use.

    Returns:
        PLSFeatureSelectionDirFmt: Serialized keepX error rates and selected
            feature counts.
    """
    r("suppressPackageStartupMessages(library(mixOmics))")
    blocks = tables.collection
    target = y.to_series().copy()
    design = _resolve_design(design_matrix, design_weight, list(blocks))
    bpparam = _build_bpparam(threads, seed)

    keepx_collection = dict(getattr(keepx, "collection", keepx))
    parsed_keepx = _parse_keepx_collection(keepx_collection, list(blocks))
    r_blocks, r_target, r_design = _to_r_inputs(blocks, target, design)
    already_tested = (
        _parse_keepx_collection(
            dict(getattr(already_tested_keepx, "collection", already_tested_keepx)),
            list(blocks),
        )
        if already_tested_keepx is not None
        else None
    )
    tune_result = _run_tune(
        r_blocks,
        r_target,
        r_design,
        ncomp,
        parsed_keepx,
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
        already_tested,
    )
    error_rates = _r_feature_selection_error_rate_to_dataframe(
        tune_result, tuple(blocks)
    )
    selected_features = _selected_features_table(tune_result)
    print("Tuned keepX values:\n", flush=True)
    print(f"{selected_features.to_string()}\n", flush=True)
    return _serialize_feature_selection(
        error_rates,
        selected_features,
    )


def feature_selection_block_splsda(
    ctx,
    tables,
    y,
    design_matrix=None,
    design_weight=None,
    tuned_ncomp=None,
    ncomp=None,
    keepx=None,
    auto_keepx=True,
    min_keepx=5,
    max_keepx_fraction=0.2,
    grid_size=5,
    refinement_factor=2.0,
    selection_rule="one_se",
    ber_margin=0.0,
    se_multiplier=1.0,
    scale=True,
    tol=1e-6,
    max_iter=100,
    near_zero_var=False,
    validation="Mfold",
    folds=10,
    nrepeat=3,
    signif_threshold=0.01,
    distance="max.dist",
    measure="BER",
    weighted=True,
    seed=None,
    threads=1,
):
    """Runs manual or adaptive DIABLO feature selection and diagnostics."""
    align_samples = ctx.get_action("mfa", "_align_samples_metadata")
    selected_ncomp = _resolve_ncomp(ncomp, tuned_ncomp, weighted, measure, distance)
    resolved_seed = secrets.randbelow(2**31) if seed is None else seed
    select_features = ctx.get_action("mfa", "_feature_selection_block_splsda")
    aligned_tables, aligned_metadata = align_samples(
        tables=tables,
        metadata_column=y,
    )
    aligned_y = aligned_metadata.view(Metadata).get_column(y.name)
    block_names = tuple(aligned_tables.collection)

    def evaluate_grid(component, grid, fixed_keepx):
        """Runs one provenance-tracked grid and returns cache-compatible rows."""
        previous = (
            {name: ",".join(map(str, values)) for name, values in fixed_keepx.items()}
            if fixed_keepx
            else None
        )
        (tuning,) = select_features(
            tables=aligned_tables,
            y=aligned_y,
            design_matrix=design_matrix,
            design_weight=design_weight,
            ncomp=component,
            keepx={name: ",".join(map(str, values)) for name, values in grid.items()},
            already_tested_keepx=previous,
            scale=scale,
            tol=tol,
            max_iter=max_iter,
            near_zero_var=near_zero_var,
            validation=validation,
            folds=folds,
            nrepeat=nrepeat,
            signif_threshold=signif_threshold,
            distance=distance,
            measure=measure,
            weighted=weighted,
            seed=resolved_seed,
            threads=threads,
        )
        error_rates = tuning.view(PLSFeatureSelectionDirFmt).error_rate.view(
            pd.DataFrame
        )
        return _error_rates_to_cache_rows(error_rates)

    if not auto_keepx:
        if keepx is None:
            raise ValueError("keepx is required when auto_keepx is false.")
        (tuning,) = select_features(
            tables=aligned_tables,
            y=aligned_y,
            design_matrix=design_matrix,
            design_weight=design_weight,
            ncomp=selected_ncomp,
            keepx=keepx,
            scale=scale,
            tol=tol,
            max_iter=max_iter,
            near_zero_var=near_zero_var,
            validation=validation,
            folds=folds,
            nrepeat=nrepeat,
            signif_threshold=signif_threshold,
            distance=distance,
            measure=measure,
            weighted=weighted,
            seed=resolved_seed,
            threads=threads,
        )
    else:
        blocks = {
            name: artifact.view(pd.DataFrame)
            for name, artifact in aligned_tables.collection.items()
        }
        target = aligned_y.to_series().copy()
        design = _resolve_design(design_matrix, design_weight, list(blocks))
        initial_keepx = (
            _parse_keepx_collection(
                dict(getattr(keepx, "collection", keepx)), list(blocks)
            )
            if keepx is not None
            else None
        )
        automatic = adaptive_keepx_refinement(
            blocks,
            target,
            design,
            selected_ncomp,
            initial_keepx=initial_keepx,
            min_keepx=min_keepx,
            max_keepx_fraction=max_keepx_fraction,
            grid_size=grid_size,
            refinement_factor=refinement_factor,
            selection_rule=selection_rule,
            ber_margin=ber_margin,
            se_multiplier=se_multiplier,
            nrepeat=nrepeat,
            evaluate_grid=evaluate_grid,
        )
        cache_rows = pd.concat(
            [
                _cache_to_error_rates(cache, component - 1)
                for component, cache in automatic.evaluation_cache.items()
            ],
            ignore_index=True,
        )
        tuning = ctx.make_artifact(
            PLSFeatureSelection,
            _serialize_feature_selection(
                _cache_rows_to_error_rates(cache_rows, block_names),
                pd.DataFrame(automatic.keep_x).rename_axis("component"),
            ),
        )
    return tuning, _feature_selection_visualization(ctx, tuning, block_names)


def _error_rates_to_cache_rows(error_rates: pd.DataFrame) -> pd.DataFrame:
    """Converts serialized feature-selection rates to strategy cache rows."""
    keepx_columns = [column for column in error_rates if column.startswith("keepx_")]
    result = error_rates.melt(
        id_vars=["component", *keepx_columns],
        value_vars=["mean", "sd"],
        var_name="statistic",
        value_name="value",
    )
    result["keepx"] = (
        result[keepx_columns].astype(int).astype(str).agg("_".join, axis=1)
    )
    return result[["keepx", "component", "statistic", "value"]]


def _cache_rows_to_error_rates(cache_rows, block_names):
    """Pivots complete adaptive cache records into the 23 artifact schema."""
    keepx_columns = [f"keepx_{name}" for name in block_names]
    result = cache_rows.pivot(
        index=["component", "keepx"], columns="statistic", values="value"
    ).reset_index()
    values = result.pop("keepx").map(lambda value: [int(v) for v in value.split("_")])
    result[keepx_columns] = pd.DataFrame(values.tolist(), index=result.index)
    return result[["component", "mean", "sd", *keepx_columns]]


def _feature_selection_visualization(ctx, tuning, block_names):
    """Creates the full-cache table and optional per-component heatmaps."""
    error_rates = tuning.view(PLSFeatureSelectionDirFmt).error_rate.view(pd.DataFrame)
    tabulate = ctx.get_action("metadata", "tabulate")
    (table,) = tabulate(input=Metadata(error_rates.set_index("id")))
    if len(block_names) != 2:
        return table
    heatmap = ctx.get_action("vizard", "heatmap")
    heatmaps = {}
    for component in sorted(error_rates["component"].unique()):
        (plot,) = heatmap(
            metadata=Metadata(
                error_rates.loc[error_rates["component"] == component].set_index("id")
            ),
            x_measure=f"keepx_{block_names[0]}",
            y_measure=f"keepx_{block_names[1]}",
            gradient_measure="mean",
            title=f"sPLS-DA keepX error rates: component {component + 1}",
        )
        heatmaps[f"Component {component + 1}"] = plot
    return ctx.make_report(
        matryoshka_template,
        {
            "Error-rate heatmaps": ctx.make_report(matryoshka_template, heatmaps),
            "All error rates": table,
        },
    )


def _parse_keepx_collection(
    keepx: dict, block_names: list[str]
) -> dict[str, list[int]]:
    """
    Parses named comma-separated keepX candidate counts.

    For example, ``{"metabolome": "5,10", "microbiome": "3,6"}``
    becomes ``{"metabolome": [5, 10], "microbiome": [3, 6]}``.

    Args:
        keepx (dict): Collection mapping each block to comma-separated feature
            counts.
        block_names (list[str]): Ordered names of the input feature blocks.

    Returns:
        dict[str, list[int]]: Validated candidate counts keyed by block name.

    Raises:
        ValueError: If the collection keys do not match the input blocks or a
            value is not a positive integer.
    """
    if set(keepx) != set(block_names):
        raise ValueError("keepx keys must exactly match input block names.")
    parsed = {}
    for name in block_names:
        try:
            values = [int(value.strip()) for value in str(keepx[name]).split(",")]
            if not values or any(value < 1 for value in values):
                raise ValueError
        except ValueError as error:
            raise ValueError(
                "Each keepx value must be a comma-separated list of positive integers."
            ) from error
        parsed[name] = values
    return parsed


def _selected_features_table(tune_result: ListVector) -> pd.DataFrame:
    """
    Creates a component-by-block selected keepX-count table from a mixOmics
    result.

    Args:
        tune_result (ListVector): Result returned by mixOmics
            ``tune.block.splsda``.

    Returns:
        pd.DataFrame: Selected feature counts with zero-based component numbers
            as the index and block names as columns.
    """
    selected_keepx = tune_result.rx2("choice.keepX")
    selected_features = pd.DataFrame(
        {
            str(block): [int(value) for value in values]
            for block, values in zip(selected_keepx.names, selected_keepx)
        }
    )
    selected_features.index.name = "component"
    return selected_features


def _r_feature_selection_error_rate_to_dataframe(
    tune_result: ListVector, block_names: tuple[str, ...]
) -> pd.DataFrame:
    """
    Converts mixOmics keepX error-rate matrices to named wide-format records.

    Reads the mean error-rate matrix and standard-deviation matrix returned by
    ``tune.block.splsda``. The R matrices use keepX combinations such as
    ``5_10`` as row names and component labels such as ``comp1`` as column
    names. This function converts each matrix to a pandas table, converts the
    one-based component labels to zero-based values, and joins the standard
    deviations to their matching means. Finally, it expands every keepX label
    into one ``keepx_<block>`` column for each input block.

    Args:
        tune_result: R ``tune.block.splsda`` result.
        block_names (tuple[str, ...]): Ordered names of the input feature
            blocks.

    Returns:
        pd.DataFrame: Component, mean, standard deviation, and one keepX
            column per input block. Each row represents one tested combination
            for one component.
    """
    statistic_tables = {}
    for statistic, error_rates in (
        ("mean", tune_result.rx2("error.rate")),
        ("sd", tune_result.rx2("error.rate.sd")),
    ):
        values = np.asarray(error_rates, dtype=float)
        keepx_values = [str(value) for value in r["dimnames"](error_rates)[0]]
        component_names = [str(value) for value in r["dimnames"](error_rates)[1]]
        component_numbers = [
            int(name.removeprefix("comp")) - 1 for name in component_names
        ]
        statistic_table = (
            pd.DataFrame(
                values.T,
                index=pd.Index(component_numbers, name="component"),
                columns=pd.Index(keepx_values, name="keepx"),
            )
            .reset_index()
            .melt(id_vars="component", var_name="keepx", value_name=statistic)
        )
        statistic_tables[statistic] = statistic_table
    result = statistic_tables["mean"].merge(
        statistic_tables["sd"], on=["keepx", "component"], how="left", sort=False
    )
    keepx_columns = [f"keepx_{name}" for name in block_names]
    parsed = result["keepx"].map(
        lambda value: [int(count) for count in str(value).split("_")]
    )
    result = result.drop(columns="keepx")
    result[keepx_columns] = pd.DataFrame(parsed.tolist(), index=result.index)
    return result[["component", "mean", "sd", *keepx_columns]]


def _run_tune(
    r_blocks: ListVector,
    r_target: FactorVector,
    r_design,
    ncomp,
    keep_x,
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
    already_tested_keepx: dict[str, list[int]] | None = None,
) -> ListVector:
    """
    Tunes DIABLO sparse feature counts for the selected components.

    Args:
        r_blocks (ListVector): Named R feature blocks.
        r_target (ListVector): Aligned R categorical target.
        r_design: R DIABLO design matrix or scalar design weight.
        ncomp: Number of components to tune.
        keep_x: Parsed candidate grids by block.
        tol: Convergence tolerance for tuning.
        max_iter: Maximum tuning iterations.
        near_zero_var: Whether to filter near-zero variance features.
        scale: Whether to scale blocks.
        validation: Cross-validation strategy.
        folds: Number of folds.
        nrepeat: Number of repeats.
        signif_threshold: Component improvement threshold.
        distance: Prediction distance used by tuning.
        measure: Error measure used by tuning.
        weighted: Whether to use weighted prediction performance.
        seed: Captured random seed.
        bpparam: R BiocParallel backend.

    Returns:
        ListVector: Result returned by mixOmics ``tune.block.splsda``.
    """
    r_keep_x = ListVector({name: IntVector(values) for name, values in keep_x.items()})
    quiet_tune = r(
        "function(...) { "
        "suppressWarnings(suppressMessages(tune.block.splsda(...))) "
        "}"
    )
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
    if already_tested_keepx:
        parameters["already.tested.X"] = ListVector(
            {name: IntVector(values) for name, values in already_tested_keepx.items()}
        )
    tune_result = quiet_tune(
        r_blocks,
        r_target,
        **parameters,
    )
    return tune_result


def _serialize_feature_selection(
    error_rate: pd.DataFrame,
    selected_features: pd.DataFrame,
) -> PLSFeatureSelectionDirFmt:
    """
    Serializes feature-selection tables as Table JSONL files.

    Attaches table descriptions that identify the mixOmics sources for the
    cross-validated error rates and selected keepX counts, then writes both
    tables into the feature-selection directory format.

    Args:
        error_rate (pd.DataFrame): Cross-validated error rates for every tested
            keepX combination and component.
        selected_features (pd.DataFrame): Selected keepX counts with components
            as rows and blocks as columns.

    Returns:
        PLSFeatureSelectionDirFmt: Directory format containing the serialized
            feature-selection tables.
    """
    directory_format = PLSFeatureSelectionDirFmt()
    error_rate = error_rate.copy()
    selected_features = selected_features.reset_index()
    error_rate.insert(
        0, "id", [f"row{index}" for index in range(1, len(error_rate) + 1)]
    )
    error_rate.attrs["description"] = jsonl_descriptions["feature_selection_error_rate"]
    selected_features.attrs["description"] = jsonl_descriptions[
        "feature_selection_selected_features"
    ]
    directory_format.error_rate.write_data(error_rate, pd.DataFrame)
    directory_format.selected_features.write_data(selected_features, pd.DataFrame)
    return directory_format
