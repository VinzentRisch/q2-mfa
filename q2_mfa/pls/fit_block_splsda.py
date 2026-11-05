# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
"""QIIME-facing DIABLO block sPLS-DA fitting action."""

import secrets
from collections.abc import Iterable

import numpy as np
import pandas as pd
from rachis import CategoricalMetadataColumn
from rachis.plugin import CaptureHolder
from rpy2.robjects import ListVector
from rpy2.robjects.packages import importr

from q2_mfa.pls.descriptions import fit_descriptions
from q2_mfa.pls.types._format import (
    PLSComponentSelectionDirFmt,
    PLSFeatureSelectionDirFmt,
    PLSFitDirFmt,
)
from q2_mfa.pls.utils import (
    _build_bpparam,
    _call_without_messages,
    _parse_keepx_collection,
    _r_matrix_to_dataframe,
    _r_perf_error_rate_to_df,
    _resolve_design,
    _resolve_ncomp,
    _to_r_inputs,
)

base = importr("base")
mixomics = importr("mixOmics")


def fit_block_splsda(
    tables: pd.DataFrame,
    y: CategoricalMetadataColumn,
    design_matrix: pd.DataFrame = None,
    design_weight: float | None = None,
    tuned_components: PLSComponentSelectionDirFmt = None,
    ncomp: CaptureHolder[int] = None,
    keepx: CaptureHolder[dict] = None,
    feature_selection: PLSFeatureSelectionDirFmt = None,
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
) -> PLSFitDirFmt:
    """Fits DIABLO with supplied or previously selected components and keepX.

    ``ncomp`` and ``tuned_components`` are mutually exclusive. Likewise,
    provide manual block-keyed ``keepx`` strings or a feature-selection
    artifact, but not both. The input tables and response must already have
    identical sample IDs in the same order.
    """
    blocks = dict(tables.items())
    target = y.to_series()
    design = _resolve_design(design_matrix, design_weight, list(blocks))
    selected_ncomp = _resolve_ncomp(
        ncomp, tuned_components, weighted, measure, distance
    )
    selected_keepx = _resolve_fit_keepx(
        keepx, feature_selection, list(blocks), selected_ncomp
    )
    resolved_seed = CaptureHolder.get_or_set(seed, lambda: secrets.randbelow(2**31))
    bpparam = _build_bpparam(threads)

    r_blocks, r_target, r_design, r_keepx, _ = _to_r_inputs(
        blocks,
        target,
        design,
        keep_x=selected_keepx,
    )
    model = _call_without_messages(
        mixomics.block_splsda,
        r_blocks,
        r_target,
        **{
            "ncomp": selected_ncomp,
            "keepX": r_keepx,
            "design": r_design,
            "scale": scale,
            "tol": tol,
            "max.iter": max_iter,
            "near.zero.var": near_zero_var,
            "all.outputs": True,
            "verbose.call": False,
        },
    )
    perf_result = _call_without_messages(
        mixomics.perf,
        model,
        **{
            "dist": "all",
            "validation": validation,
            "folds": folds,
            "nrepeat": nrepeat,
            "signif.threshold": signif_threshold,
            "auc": True,
            "BPPARAM": bpparam,
            "seed": resolved_seed,
            "progressBar": False,
        },
    )
    return _serialize_fit(model, perf_result)


def _serialize_fit(model, perf_result) -> PLSFitDirFmt:
    """Serializes final DIABLO model and performance outputs to JSONL files."""
    loadings = _r_named_frames(model.rx2("loadings"))
    variates = _r_named_frames(model.rx2("variates"))
    weights = _r_matrix_to_dataframe(base.as_matrix(model.rx2("weights")))
    # mixOmics changes weight row names but retains the input block order
    weights.index = pd.Index([str(name) for name in model.rx2("X").names], name="block")
    prop_expl_var = model.rx2("prop_expl_var")
    directory_format = PLSFitDirFmt()
    _write_fit_table(
        directory_format.loadings,
        _block_wide_values(loadings, "feature", "loading"),
        "loadings",
    )
    _write_fit_table(
        directory_format.variates,
        _block_wide_values(variates, "sample", "score"),
        "variates",
    )
    _write_fit_table(
        directory_format.weights,
        _component_vectors_to_dataframe(weights.iterrows(), "weight"),
        "weights",
    )
    _write_fit_table(
        directory_format.consensus_variates,
        _block_wide_values(
            _consensus_variates(variates, weights), "sample", "score"
        ).rename(columns={"block": "method"}),
        "consensus_variates",
    )
    _write_fit_table(
        directory_format.prop_expl_var,
        _component_vectors_to_dataframe(
            zip(prop_expl_var.names, prop_expl_var),
            "proportion_explained_variance",
        ),
        "prop_expl_var",
    )
    _write_fit_table(
        directory_format.ave,
        _r_ave_to_dataframe(model.rx2("AVE")),
        "ave",
    )
    _write_fit_table(
        directory_format.crit,
        _r_criterion_to_dataframe(model.rx2("crit")),
        "crit",
    )
    _write_fit_table(
        directory_format.feature_stability,
        _r_feature_stability_to_dataframe(perf_result.rx2("features").rx2("stable")),
        "feature_stability",
    )
    _write_fit_table(
        directory_format.auc, _r_auc_to_dataframe(perf_result.rx2("auc")), "auc"
    )
    _write_fit_table(
        directory_format.error_rate_weighted,
        _r_perf_error_rate_to_df(perf_result, "WeightedVote"),
        "error_rate_weighted",
    )
    _write_fit_table(
        directory_format.error_rate_majority,
        _r_perf_error_rate_to_df(perf_result, "MajorityVote"),
        "error_rate_majority",
    )
    correlations = _feature_component_correlations(
        _r_named_frames(model.rx2("X")), variates, loadings
    )
    _write_fit_table(
        directory_format.feature_component_correlation,
        _block_wide_values(correlations, "feature", "correlation"),
        "feature_component_correlation",
    )
    _write_fit_table(
        directory_format.feature_similarity,
        _feature_similarity_to_dataframe(correlations),
        "feature_similarity",
    )
    return directory_format


def _consensus_variates(
    variates: dict[str, pd.DataFrame], weights: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    """Averages aligned input-block scores using equal or signed model weights.

    The weight index identifies the input blocks, excluding the outcome Y.
    Each weighted score is divided by the sum of weights for its component,
    matching mixOmics plotIndiv().
    """
    first = variates[weights.index[0]]
    scores = np.stack(
        [
            variates[block].loc[first.index, first.columns].to_numpy()
            for block in weights.index
        ]
    )
    block_weights = weights.loc[:, first.columns].to_numpy()
    return {
        "average": pd.DataFrame(
            scores.mean(axis=0), index=first.index, columns=first.columns
        ),
        "weighted_average": pd.DataFrame(
            (scores * block_weights[:, None, :]).sum(axis=0)
            / block_weights.sum(axis=0),
            index=first.index,
            columns=first.columns,
        ),
    }


def _write_fit_table(directory_file, table: pd.DataFrame, description_key: str) -> None:
    ids = pd.array([str(index) for index in range(1, len(table) + 1)], dtype="string")
    table.insert(0, "id", ids)
    table.attrs["description"] = fit_descriptions[description_key]
    directory_file.write_data(table, pd.DataFrame)


def _resolve_fit_keepx(
    keepx: CaptureHolder[dict], feature_selection, block_names: list[str], ncomp: int
) -> dict[str, list[int]]:
    """Captures keepX strings supplied manually or derived from an artifact."""
    manual_keepx = keepx is not None and (
        not isinstance(keepx, CaptureHolder) or keepx.is_set
    )
    if manual_keepx == (feature_selection is not None):
        raise ValueError("Provide exactly one of 'keepx' or 'feature-selection'.")
    block_keepx = CaptureHolder.get_or_set(
        keepx,
        lambda: _block_keepx_from_feature_selection(feature_selection, ncomp),
    )
    parsed = _parse_keepx_collection(block_keepx, block_names, ncomp)
    if manual_keepx and any(len(counts) != ncomp for counts in parsed.values()):
        raise ValueError(
            f"Each keepx block must provide exactly {ncomp} feature counts, "
            "one for each fitted component."
        )
    return parsed


def _block_keepx_from_feature_selection(
    feature_selection, ncomp: int
) -> dict[str, str]:
    """Reads the wide keepX table into block-keyed parameter strings.

    Orders the counts within each block by one-based component label.
    """
    table = feature_selection.selected_features.view(pd.DataFrame)
    expected_components = list(range(1, ncomp + 1))
    if sorted(table["component"]) != expected_components:
        raise ValueError(
            "The feature-selection artifact must contain one row per fitted "
            "component."
        )
    table = table.drop(columns="id", errors="ignore").set_index("component")
    table = table.loc[expected_components]
    return {
        block: ",".join(str(int(value)) for value in table[block]) for block in table
    }


def _block_wide_values(
    tables: dict[str, pd.DataFrame], identifier: str, value_name: str
) -> pd.DataFrame:
    """Reshapes block-specific feature or sample tables into long records.

    Args:
        tables (dict[str, pd.DataFrame]): Wide tables keyed by block name.
        identifier (str): Output column for the index, like ``feature``.
        value_name (str): Output column for the numeric values like ``loading``.

    Returns:
        pd.DataFrame: Columns ``block``, the requested identifier,
            ``component``, and the requested value name.

    Example:
        >>> tables = {"gene": pd.DataFrame([[0.2, 0.4]], index=["feature_a"])}
        >>> _block_wide_values(tables, "feature", "loading")
          block    feature  component  loading
        0  gene  feature_a          1      0.2
        1  gene  feature_a          2      0.4
    """
    records = []
    for block, table in tables.items():
        working = table.copy()
        working.index.name = identifier
        working.columns = range(1, working.shape[1] + 1)
        long_table = working.reset_index().melt(
            id_vars=[identifier], var_name="component", value_name=value_name
        )
        long_table["component"] = long_table["component"].astype("int64")
        long_table.insert(0, "block", str(block))
        records.append(long_table)
    columns = ["block", identifier, "component", value_name]
    if not records:
        return pd.DataFrame(columns=columns)
    combined = pd.concat(records, ignore_index=True)[columns]
    combined[identifier] = combined[identifier].astype(str)
    return combined


def _r_named_frames(values: ListVector) -> dict[str, pd.DataFrame]:
    """Converts each matrix in a named R list to a wide pandas table.

    Preserves R list names as dictionary keys and matrix row and column
    labels as DataFrame labels.

    Args:
        values: Named R list of numeric matrices with row and column labels.

    Returns:
        dict[str, pd.DataFrame]: One wide table per R list entry, with string
            keys and labels in their original order.
    """
    return {
        str(name): _r_matrix_to_dataframe(value)
        for name, value in zip(values.names, values)
    }


def _component_vectors_to_dataframe(
    vectors: Iterable[tuple[str, Iterable[float]]], value_name: str
) -> pd.DataFrame:
    """Flattens one numeric vector per block into component records.

    Example:
        >>> _component_vectors_to_dataframe([("gene", [0.2, 0.4])], "weight")
          block  component  weight
        0  gene          1     0.2
        1  gene          2     0.4
    """
    return pd.DataFrame.from_records(
        (
            (str(block), component, float(value))
            for block, values in vectors
            for component, value in enumerate(values, start=1)
        ),
        columns=["block", "component", value_name],
    )


def _r_ave_to_dataframe(values) -> pd.DataFrame:
    """Flattens block and overall AVE vectors into one labelled table."""
    ave_x = values.rx2("AVE_X")
    tables = []
    for metric, vectors in (
        ("AVE_X", zip(ave_x.names, ave_x)),
        ("AVE_outer", [("overall", values.rx2("AVE_outer"))]),
        ("AVE_inner", [("overall", values.rx2("AVE_inner"))]),
    ):
        table = _component_vectors_to_dataframe(vectors, "value")
        table.insert(0, "metric", metric)
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def _r_criterion_to_dataframe(values) -> pd.DataFrame:
    """Flattens per-component convergence traces into one pandas table.

    Args:
        values: Unnamed R list of numeric convergence criteria, one per
            component.

    Returns:
        pd.DataFrame: Component, iteration, and criterion values.
    """
    return pd.DataFrame.from_records(
        (
            (component, iteration, float(criterion))
            for component, trace in enumerate(values, start=1)
            for iteration, criterion in enumerate(trace, start=1)
        ),
        columns=["component", "iteration", "criterion"],
    )


def _r_feature_stability_to_dataframe(stable) -> pd.DataFrame:
    """Averages selection frequencies across all CV repeats.

    A feature omitted from a repeat was selected in zero folds, so its
    contribution is zero and the repeat still counts in the denominator.

    Args:
        stable: R selection frequencies nested by repeat, block, and component
            from ``perf_result$features$stable``.

    Returns:
        pd.DataFrame: Block, feature, component, and mean selection frequency.
    """
    records = []
    for repeat_values in stable:
        for block_name, component_values in zip(repeat_values.names, repeat_values):
            for component, selection_frequency in enumerate(component_values, start=1):
                feature_names = [str(name) for name in base.names(selection_frequency)]
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
    stability = (
        pd.concat(records, ignore_index=True)
        .groupby(["block", "feature", "component"], as_index=False)
        .agg(mean_selection_frequency=("selection_frequency", "sum"))
    )
    stability["mean_selection_frequency"] /= len(stable)
    return stability


def _r_auc_to_dataframe(auc) -> pd.DataFrame:
    """Converts mixOmics per-component, per-contrast AUC results.

    Args:
        auc: R list of per-component AUC matrices from ``perf_result$auc``.

    Returns:
        pd.DataFrame: Component, contrast, AUC, and p-value records.
    """
    columns = ["component", "contrast", "auc", "p_value"]
    records = []
    for component, values in enumerate(auc, start=1):
        auc_table = (
            _r_matrix_to_dataframe(values)
            .rename(columns={"AUC": "auc", "p-value": "p_value"})
            .rename_axis("contrast")
            .reset_index()
        )
        auc_table.insert(0, "component", component)
        records.append(auc_table[columns])
    return pd.concat(records, ignore_index=True)


def _feature_component_correlations(
    blocks: dict[str, pd.DataFrame],
    variates: dict[str, pd.DataFrame],
    loadings: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Returns feature-by-component Pearson correlations for each fitted block.

    Selects features with a nonzero loading on any fitted component. Each
    correlation uses the samples with both a feature value and a component
    score, as in mixOmics ``circosPlot()``.
    """
    correlations = {}
    for block, values in blocks.items():
        block_loadings = loadings[block]
        selected = block_loadings.index[block_loadings.fillna(0).ne(0).any(axis=1)]
        feature_values = values.loc[:, selected]
        block_variates = variates[block]
        correlations[block] = pd.DataFrame(
            {
                component: feature_values.corrwith(scores)
                for component, (_, scores) in enumerate(block_variates.items(), start=1)
            }
        )
    return correlations


def _feature_similarity_to_dataframe(
    correlations: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Returns one dot product of component correlations per feature pair."""
    combined = pd.concat(correlations, names=["block", "feature"])
    blocks = combined.index.get_level_values("block")
    features = combined.index.get_level_values("feature")
    values = combined.to_numpy()
    first, second = np.triu_indices(len(combined), k=1)
    return pd.DataFrame(
        {
            "block_1": blocks[first],
            "feature_1": features[first],
            "block_2": blocks[second],
            "feature_2": features[second],
            "similarity": (values @ values.T)[first, second],
        }
    )
