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
from rachis import Artifact, CategoricalMetadataColumn, Metadata, Visualization
from rachis.plugin import CaptureHolder
from rachis.plugin.context import IContext
from rpy2.robjects import ListVector, r

from q2_mfa.pls.jsonl_descriptions import jsonl_descriptions
from q2_mfa.pls.types._format import PLSFeatureSelectionDirFmt, PLSTuneComponentsDirFmt
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
    already_tested_x: dict | None = None,
    design_matrix: Metadata = None,
    design_weight: float | None = None,
    tuned_ncomp: PLSTuneComponentsDirFmt = None,
    ncomp: CaptureHolder[int] = None,
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
    seed: CaptureHolder[int] = None,
    threads: int = 1,
) -> PLSFeatureSelectionDirFmt:
    """
    Tunes block sPLS-DA (DIABLO) sparse feature counts with mixOmics.

    Assumes the input blocks and categorical response have already been sample
    aligned, determines the component count from either ``ncomp`` or a
    component-tuning artifact, evaluates the supplied manual keepX candidate
    grid, and serializes error rates and the selected sparse-feature counts.

    Args:
        tables (ResultCollection): Named feature-table artifacts used as
            blocks for block sPLS-DA (DIABLO).
        y (CategoricalMetadataColumn): Categorical response labels for the
            samples.
        keepx (dict): Named comma-separated keepX candidate counts for each
            input block.
        already_tested_x (dict, optional): Named comma-separated selected
            keepX counts for earlier components. Each block must provide the
            same number of prior component selections.
        design_matrix (Metadata, optional): Explicit block-relationship design
            matrix.
        design_weight (float, optional): Shared off-diagonal relationship
            weight used when no design matrix is supplied.
        tuned_ncomp (PLSTuneComponentsDirFmt, optional): Component-tuning
            artifact used when ``ncomp`` is not provided.
        ncomp (CaptureHolder[int], optional): Manual number of components to
            tune.
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
        seed (CaptureHolder[int], optional): Random seed holder used for
            reproducible cross-validation.
        threads (int): Number of BiocParallel workers to use.

    Returns:
        PLSFeatureSelectionDirFmt: Serialized keepX error rates and selected
            feature counts.
    """
    r("suppressPackageStartupMessages(library(mixOmics))")
    blocks = tables.collection
    target = y.to_series()
    design = _resolve_design(design_matrix, design_weight, list(blocks))
    resolved_seed = CaptureHolder.get_or_set(seed, lambda: secrets.randbelow(2**31))
    bpparam = _build_bpparam(threads, resolved_seed)
    selected_ncomp = _resolve_ncomp(ncomp, tuned_ncomp, weighted, measure, distance)

    keepx_collection = dict(getattr(keepx, "collection", keepx))
    parsed_keepx = _parse_keepx_collection(
        keepx_collection, list(blocks), selected_ncomp
    )
    if already_tested_x is not None:
        already_tested_x = _parse_keepx_collection(
            dict(getattr(already_tested_x, "collection", already_tested_x)),
            list(blocks),
            selected_ncomp,
            already_tested=True,
        )
    r_blocks, r_target, r_design, r_keep_x, r_already_tested_x = _to_r_inputs(
        blocks, target, design, parsed_keepx, already_tested_x
    )
    tune_parameters = {
        "ncomp": selected_ncomp,
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
        "seed": resolved_seed,
    }
    if r_already_tested_x is not None:
        tune_parameters["already.tested.X"] = r_already_tested_x
    tune_result = r(
        "function(...) suppressWarnings(suppressMessages(tune.block.splsda(...)))"
    )(r_blocks, r_target, **tune_parameters)
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
    ctx: IContext,
    tables: dict[str, Artifact],
    y: CategoricalMetadataColumn,
    keepx: dict,
    already_tested_x: dict = None,
    design_matrix: Metadata = None,
    design_weight: float = None,
    tuned_ncomp: Artifact = None,
    ncomp: CaptureHolder[int] = None,
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
) -> tuple[Artifact, Visualization]:
    """
    Selects block sPLS-DA (DIABLO) features and creates visualizations.

    Aligns the input feature tables and categorical response, resolves the
    number of components from either a manual value or a component-tuning
    artifact, runs the private feature-selection action, and delegates report
    generation to the private feature-selection visualization pipeline.

    Args:
        ctx (Context): Pipeline execution context used to retrieve actions.
        tables (ResultCollection): Named feature-table artifacts used as
            blocks for block sPLS-DA (DIABLO).
        y (CategoricalMetadataColumn): Categorical response labels for the
            samples.
        keepx (dict): Named comma-separated keepX candidate counts for each
            input block.
        already_tested_x (dict, optional): Named comma-separated selected
            keepX counts for earlier components.
        design_matrix (Metadata, optional): Explicit block-relationship design
            matrix.
        design_weight (float, optional): Shared off-diagonal relationship
            weight used when no design matrix is supplied.
        tuned_ncomp (Artifact, optional): Component-tuning artifact used when
            ``ncomp`` is not provided.
        ncomp (CaptureHolder[int], optional): Manual number of components to
            tune or holder for the value resolved from ``tuned_ncomp``.
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
        seed (int, optional): Random seed used for reproducible
            cross-validation.
        threads (int): Number of BiocParallel workers to use.

    Returns:
        tuple[Artifact, Visualization]: The feature-selection artifact and its
            diagnostic visualization.
    """
    select_features = ctx.get_action("mfa", "_feature_selection_block_splsda")
    align_samples = ctx.get_action("mfa", "_align_samples_metadata")
    visualise = ctx.get_action("mfa", "_feature_selection_block_splsda_visualiser")

    aligned_tables, aligned_metadata = align_samples(
        tables=tables,
        metadata_column=y,
    )
    selected_ncomp = _resolve_ncomp(ncomp, tuned_ncomp, weighted, measure, distance)
    (feature_selection,) = select_features(
        tables=aligned_tables,
        y=aligned_metadata.view(Metadata).get_column(y.name),
        keepx=keepx,
        already_tested_x=already_tested_x,
        design_matrix=design_matrix,
        design_weight=design_weight,
        ncomp=selected_ncomp,
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
        seed=seed,
        threads=threads,
    )
    (visualization,) = visualise(feature_selection=feature_selection)
    return feature_selection, visualization


def _feature_selection_block_splsda_visualiser(ctx, feature_selection):
    """
    Creates block sPLS-DA (DIABLO) feature-selection visualizations.

    Always tabulates all cross-validated error rates and selected feature
    counts. When the artifact contains exactly two input blocks, it
    additionally creates one heatmap per component using the two blocks'
    keepX values as axes and mean error rate as the gradient, then combines the
    plots and tables into a nested report.

    Args:
        ctx (Context): Pipeline execution context used to retrieve actions and
            create reports.
        feature_selection (Artifact): Block sPLS-DA (DIABLO)
            feature-selection results.

    Returns:
        Visualization: A report containing both tables and, for exactly two
            blocks, the component heatmaps.
    """
    tabulate = ctx.get_action("metadata", "tabulate")
    feature_selection_data = feature_selection.view(PLSFeatureSelectionDirFmt)
    error_rates = feature_selection_data.error_rate.view(Metadata)
    selected_features = feature_selection_data.selected_features.view(Metadata)
    (error_rate_table,) = tabulate(input=error_rates)
    (selected_features_table,) = tabulate(input=selected_features)

    error_rate_table_data = error_rates.to_dataframe()
    block_columns = [
        column
        for column in error_rate_table_data.columns
        if column.startswith("keepx_")
    ]
    if len(block_columns) != 2:
        return ctx.make_report(
            matryoshka_template,
            {
                "Error rates": error_rate_table,
                "Selected features": selected_features_table,
            },
        )

    heatmap = ctx.get_action("vizard", "heatmap")
    heatmaps = {}
    for component_value in sorted(error_rate_table_data["component"].unique()):
        component = int(component_value)
        component_error_rates = error_rate_table_data.loc[
            error_rate_table_data["component"] == component_value
        ]
        (component_heatmap,) = heatmap(
            metadata=Metadata(component_error_rates),
            x_measure=block_columns[0],
            y_measure=block_columns[1],
            gradient_measure="mean",
            title=(
                "block sPLS-DA (DIABLO) keepX error rates: " f"component {component}"
            ),
        )
        heatmaps[f"Component {component}"] = component_heatmap

    heatmap_report = ctx.make_report(matryoshka_template, heatmaps)
    return ctx.make_report(
        matryoshka_template,
        {
            "Error-rate heatmaps": heatmap_report,
            "Error rates": error_rate_table,
            "Selected features": selected_features_table,
        },
    )


def _parse_keepx_collection(
    keepx: dict,
    block_names: list[str],
    ncomp: int,
    already_tested: bool = False,
) -> dict[str, list[int]]:
    """
    Parses named comma-separated keepX candidate counts.

    For example, ``{"metabolome": "5,10", "microbiome": "3,6"}``
    becomes ``{"metabolome": [5, 10], "microbiome": [3, 6]}``.

    Args:
        keepx (dict): Collection mapping each block to comma-separated feature
            counts.
        block_names (list[str]): Ordered names of the input feature blocks.
        ncomp (int): Total components being tuned.
        already_tested (bool): Whether the values are fixed selections for
            earlier components rather than candidate counts.

    Returns:
        dict[str, list[int]]: Validated candidate counts keyed by block name.

    Raises:
        ValueError: If the collection keys do not match the input blocks, a
            value is not a positive integer, fixed selections have unequal
            lengths, or ncomp does not exceed their length.
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
    if already_tested:
        selection_lengths = {len(values) for values in parsed.values()}
        if len(selection_lengths) != 1:
            raise ValueError(
                "Each 'already-tested-x' value must contain the same number of "
                "component selections."
            )
        if ncomp <= selection_lengths.pop():
            raise ValueError(
                "'ncomp' must be greater than the number of 'already-tested-x' "
                "component selections."
            )
    return parsed


def _selected_features_table(tune_result: ListVector) -> pd.DataFrame:
    """
    Creates a component-by-block selected keepX-count table from a mixOmics
    result.

    Args:
        tune_result (ListVector): Result returned by mixOmics
            ``tune.block.splsda``.

    Returns:
        pd.DataFrame: Selected feature counts with one-based component numbers
            as the index and block names as columns.
    """
    selected_keepx = tune_result.rx2("choice.keepX")
    selected_features = pd.DataFrame(
        {
            str(block): [int(value) for value in values]
            for block, values in zip(selected_keepx.names, selected_keepx)
        }
    )
    selected_features.index = pd.Index(
        range(1, len(selected_features) + 1), dtype="Int64", name="component"
    )
    return selected_features


def _r_feature_selection_error_rate_to_dataframe(
    tune_result: ListVector, block_names: tuple[str, ...]
) -> pd.DataFrame:
    """
    Converts mixOmics keepX error-rate matrices to named wide-format records.

    Reads the mean error-rate matrix and standard-deviation matrix returned by
    ``tune.block.splsda``. The R matrices use keepX combinations such as
    ``5_10`` as row names and component labels such as ``comp1`` as column
    names. This function converts each matrix to a pandas table, preserves the
    one-based component labels, and joins the standard
    deviations to their matching means. Finally, it expands every keepX label
    into one ``keepx_<block>`` column for each input block.

    Args:
        tune_result: R ``tune.block.splsda`` result.
        block_names (tuple[str, ...]): Ordered names of the input feature
            blocks.

    Returns:
        pd.DataFrame: One keepX column per input block, followed by component,
            mean, and standard deviation. Each row represents one tested
            combination for one component.
    """
    statistic_tables = {}
    for statistic, error_rates in (
        ("mean", tune_result.rx2("error.rate")),
        ("sd", tune_result.rx2("error.rate.sd")),
    ):
        values = np.asarray(error_rates, dtype=float)
        keepx_values = [str(value) for value in r["dimnames"](error_rates)[0]]
        component_names = [str(value) for value in r["dimnames"](error_rates)[1]]
        component_numbers = [int(name.removeprefix("comp")) for name in component_names]
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
    result["component"] = result["component"].astype("Int64")
    return result[[*keepx_columns, "component", "mean", "sd"]]


def _serialize_feature_selection(
    error_rate: pd.DataFrame,
    selected_features: pd.DataFrame,
) -> PLSFeatureSelectionDirFmt:
    """
    Serializes feature-selection tables as Table JSONL files.

    Adds stable IDs to both tables, attaches descriptions that identify the
    mixOmics sources, and writes both tables into the feature-selection
    directory format.

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
    selected_features.insert(
        0,
        "id",
        [f"row{index}" for index in range(1, len(selected_features) + 1)],
    )
    error_rate.attrs["description"] = jsonl_descriptions["feature_selection_error_rate"]
    selected_features.attrs["description"] = jsonl_descriptions[
        "feature_selection_selected_features"
    ]
    directory_format.error_rate.write_data(error_rate, pd.DataFrame)
    directory_format.selected_features.write_data(selected_features, pd.DataFrame)
    return directory_format
