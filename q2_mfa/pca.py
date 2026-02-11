# ----------------------------------------------------------------------------
# Copyright (c) 2026, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd
import skbio
from skbio import OrdinationResults
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def pca(
    table: pd.DataFrame,
) -> skbio.OrdinationResults:
    """
    Performs a PCA analysis on a feature table and returns an OrdinationResults object
    containing the sample scores, feature loadings, eigenvalues, and proportion of
    variance explained.

    Args:
        table (pd.DataFrame): feature table

    Output:
        skbio.OrdinationResults: PCA results containing sample scores, feature loadings,
        eigenvalues, and proportion of variance explained.
    """

    # Scale
    scaler = StandardScaler()
    table_scaled = scaler.fit_transform(table)

    # PCA
    pca = PCA()
    table_pca = pca.fit_transform(table_scaled)

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
