# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import secrets

import pandas as pd
import prince
from rachis.plugin import CaptureHolder
from skbio import OrdinationResults

from q2_mfa.types import ComponentAnalysisDirFmt


def resolve_random_state(random_state: CaptureHolder[int], engine: str):
    if engine == "sklearn":
        return CaptureHolder.get_or_set(random_state, lambda: secrets.randbits(32))
    return CaptureHolder.get_or_set(random_state, lambda: None)


def pca(
    table: pd.DataFrame,
    rescale_with_mean: bool = True,
    rescale_with_std: bool = True,
    n_components: int = 2,
    n_iter: int = 3,
    random_state: CaptureHolder[int] = None,
    engine: str = "sklearn",
) -> ComponentAnalysisDirFmt:
    """
    Perform principal component analysis with prince.
    """
    random_state = resolve_random_state(random_state, engine)

    pca_params = locals()
    pca_params.pop("table")

    pca = prince.PCA(copy=True, check_input=True, **pca_params).fit(table)

    ordination = OrdinationResults(
        short_method_name="PCA",
        long_method_name="Principal Component Analysis",
        eigvals=pd.Series(pca.eigenvalues_),
        samples=pca.row_coordinates(table),
        features=pca.column_coordinates_,
        proportion_explained=pd.Series(pca.percentage_of_variance_),
    )

    results = ComponentAnalysisDirFmt()
    results.ordination.write_data(ordination, OrdinationResults)
    numeric_outputs = {
        results.sample_cosine_similarities: pca.row_cosine_similarities(table),
        results.sample_contributions: pca.row_contributions_,
        results.feature_correlations: pca.column_correlations,
        results.feature_contributions: pca.column_contributions_,
        results.feature_cosine_similarities: pca.column_cosine_similarities_,
    }
    for output, data in numeric_outputs.items():
        output.write_data(data, pd.DataFrame)

    return results
