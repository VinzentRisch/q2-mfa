# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import warnings
from functools import reduce

import pandas as pd
import prince
from rachis.plugin import CaptureHolder
from skbio import OrdinationResults

from q2_mfa.pca import resolve_random_state
from q2_mfa.types import ComponentAnalysisDirFmt


def _build_prince_input(
    feature_tables: dict,
) -> tuple[pd.DataFrame, dict]:
    feature_tables = getattr(feature_tables, "collection", feature_tables)

    if len(feature_tables) < 2:
        raise ValueError("MFA requires at least two feature tables.")

    for group_name in feature_tables:
        if ":" in group_name:
            raise ValueError("MFA group names cannot contain ':'.")

    tables = list(feature_tables.values())
    consensus_samples = reduce(
        lambda shared, table: shared.intersection(table.index),
        tables[1:],
        tables[0].index,
    )

    if consensus_samples.empty:
        raise ValueError("Feature tables do not share any sample IDs.")

    prefixed_tables = []
    groups = {}
    for group_name, table in feature_tables.items():
        dropped_samples = table.index.difference(consensus_samples)
        if not dropped_samples.empty:
            warnings.warn(
                f"\n\033[93mDropping samples from group '{group_name}' that are not "
                f"shared across all tables:\n{', '.join(dropped_samples)}\033[0m",
                UserWarning,
            )

        table = table.loc[consensus_samples].copy()
        table.columns = [f"{group_name}:{feature}" for feature in table.columns]
        prefixed_tables.append(table)
        groups[group_name] = list(table.columns)

    return pd.concat(prefixed_tables, axis=1), groups


def mfa(
    feature_tables: pd.DataFrame,
    rescale_with_mean: bool = True,
    rescale_with_std: bool = True,
    n_components: int = 2,
    n_iter: int = 3,
    random_state: CaptureHolder[int] = None,
    engine: str = "sklearn",
) -> ComponentAnalysisDirFmt:
    """
    Run Multiple Factor Analysis with the prince package.
    """
    random_state = resolve_random_state(random_state, engine)

    mfa_params = locals()
    mfa_params.pop("feature_tables")

    table, groups = _build_prince_input(feature_tables)

    mfa_result = prince.MFA(**mfa_params).fit(table, groups=groups)

    ordination = OrdinationResults(
        short_method_name="MFA",
        long_method_name="Multiple Factor Analysis",
        eigvals=pd.Series(mfa_result.eigenvalues_),
        samples=mfa_result.row_coordinates(table),
        features=mfa_result.column_coordinates_,
        proportion_explained=pd.Series(mfa_result.percentage_of_variance_),
    )
    results = ComponentAnalysisDirFmt()
    results.ordination.write_data(ordination, OrdinationResults)
    numeric_outputs = {
        results.partial_sample_coordinates: mfa_result.partial_row_coordinates(table),
        results.sample_cosine_similarities: mfa_result.row_cosine_similarities(table),
        results.sample_contributions: mfa_result.row_contributions_,
        results.group_coordinates: mfa_result.group_coordinates_,
        results.group_contributions: mfa_result.group_contributions_,
        results.group_cosine_similarities: mfa_result.group_cosine_similarities_,
        results.partial_correlations: mfa_result.partial_correlations_,
        results.partial_contributions: mfa_result.partial_contributions_,
        results.feature_correlations: mfa_result.column_correlations,
        results.feature_contributions: mfa_result.column_contributions_,
        results.feature_cosine_similarities: mfa_result.column_cosine_similarities_,
    }
    for output, data in numeric_outputs.items():
        output.write_data(data, pd.DataFrame)

    return results
