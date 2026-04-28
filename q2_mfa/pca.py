# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import secrets

import pandas as pd
import skbio
from rachis.plugin import CaptureHolder
from skbio import OrdinationResults
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def pca(
    table: pd.DataFrame,
    n_components: int | None = None,
    svd_solver: str = "full",
    random_state: CaptureHolder[int] = None,
    scale_std: bool = False,
) -> skbio.OrdinationResults:
    """
    Perform principal component analysis with sklearn and return ordination results.

    Args:
        table (pd.DataFrame): Feature table with samples as rows and features as
            columns.
        n_components (int | None): Number of components to keep, or ``None`` to
            keep all components.
        svd_solver (str): Solver used by sklearn PCA.
        random_state (CaptureHolder[int] | int | None): Random seed used by
            stochastic solvers. If not provided, a seed is generated and
            captured by Rachis.
        scale_std (bool): If ``True``, scale features to unit variance with
            ``StandardScaler(with_mean=False, with_std=True)`` before PCA.

    Returns:
        skbio.OrdinationResults: PCA results containing sample scores, feature
            loadings, eigenvalues, and proportion of variance explained.
    """
    if svd_solver == "randomized":
        random_state = CaptureHolder.get_or_set(
            random_state, lambda: secrets.randbits(32)
        )
    else:
        random_state = CaptureHolder.get_or_set(random_state, lambda: None)

    if scale_std:
        table = pd.DataFrame(
            StandardScaler(with_mean=False, with_std=True).fit_transform(table),
            index=table.index,
            columns=table.columns,
        )

    pca = PCA(
        n_components=n_components,
        svd_solver=svd_solver,
        random_state=random_state,
    )
    table_pca = pca.fit_transform(table)

    # Build ordination pieces

    # Sample scores (Site)
    samples = pd.DataFrame(
        table_pca,
        index=table.index,
        columns=[f"PC{i + 1}" for i in range(pca.n_components_)],
    )

    # Feature loadings (Species)
    features = pd.DataFrame(
        pca.components_.T, index=table.columns, columns=samples.columns
    )

    # Eigenvalues
    eigvals = pd.Series(pca.explained_variance_, index=samples.columns)

    # Explained variance ratio
    proportion_explained = pd.Series(
        pca.explained_variance_ratio_, index=samples.columns
    )

    # Create OrdinationResults object
    ordination = OrdinationResults(
        short_method_name="PCA",
        long_method_name="Principal Component Analysis",
        eigvals=eigvals,
        samples=samples,
        features=features,
        proportion_explained=proportion_explained,
    )

    return ordination
