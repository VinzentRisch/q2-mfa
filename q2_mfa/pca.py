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
import skbio
from rachis.plugin import CaptureHolder
from skbio import OrdinationResults


def pca(
    table: pd.DataFrame,
    rescale_with_mean: bool = True,
    rescale_with_std: bool = False,
    n_components: int = 2,
    n_iter: int = 3,
    random_state: CaptureHolder[int] = None,
    engine: str = "sklearn",
) -> skbio.OrdinationResults:
    """
    Perform principal component analysis with prince and return ordination results.

    Args:
        table (pd.DataFrame): Feature table with samples as rows and features as
            columns.
        rescale_with_mean (bool): Whether to subtract each column's mean before
            performing SVD.
        rescale_with_std (bool): Whether to standardize each column before
            performing SVD.
        n_components (int): Number of principal components to compute.
        n_iter (int): Number of iterations used for computing the SVD.
        random_state (CaptureHolder[int] | int | None): Random seed used by
            stochastic SVD engines. If not provided for the sklearn engine, a
            seed is generated and captured in provenance.
        engine (str): SVD engine used by prince.

    Returns:
        skbio.OrdinationResults: PCA results containing sample scores, feature
            coordinates, eigenvalues, and percentage of variance explained.
    """
    if engine == "sklearn":
        random_state = CaptureHolder.get_or_set(
            random_state, lambda: secrets.randbits(32)
        )
    else:
        random_state = CaptureHolder.get_or_set(random_state, lambda: None)

    pca = prince.PCA(
        rescale_with_mean=rescale_with_mean,
        rescale_with_std=rescale_with_std,
        n_components=n_components,
        n_iter=n_iter,
        copy=True,
        check_input=True,
        random_state=random_state,
        engine=engine,
    ).fit(table)

    ordination = OrdinationResults(
        short_method_name="PCA",
        long_method_name="Principal Component Analysis",
        eigvals=pd.Series(pca.eigenvalues_),
        samples=pca.row_coordinates(table),
        features=pca.column_coordinates_,
        proportion_explained=pd.Series(pca.percentage_of_variance_),
    )

    return ordination
