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


def pca(
    table: pd.DataFrame,
    n_components: int | float | str | None = None,
    svd_solver: str = "auto",
    tol: float = 0.0,
    iterated_power: int | str = "auto",
    n_oversamples: int = 10,
    power_iteration_normalizer: str = "auto",
    random_state: int | None = None,
) -> skbio.OrdinationResults:
    """
    Perform principal component analysis with sklearn and return ordination results.

    Args:
        table (pd.DataFrame): Feature table with samples as rows and features as
            columns.
        n_components (int | float | str | None): Number of components to keep.
            Accepts an integer count, a variance fraction in ``(0, 1)``,
            ``"mle"``, or ``None`` to keep all components.
        svd_solver (str): Solver used by sklearn PCA.
        tol (float): Tolerance for singular values when
            ``svd_solver="arpack"``.
        iterated_power (int | str): Number of power iterations for
            ``svd_solver="randomized"``, or ``"auto"``.
        n_oversamples (int): Additional random vectors used by the randomized
            solver.
        power_iteration_normalizer (str): Power iteration normalizer used by
            the randomized solver.
        random_state (int | None): Random seed used by stochastic solvers.

    Returns:
        skbio.OrdinationResults: PCA results containing sample scores, feature
            loadings, eigenvalues, and proportion of variance explained.
    """
    pca = PCA(
        n_components=n_components,
        svd_solver=svd_solver,
        tol=tol,
        iterated_power=iterated_power,
        n_oversamples=n_oversamples,
        power_iteration_normalizer=power_iteration_normalizer,
        random_state=random_state,
    )
    try:
        table_pca = pca.fit_transform(table)
    except ValueError as error:
        raise ValueError(f"Wrong PCA parameter combination: {error}") from error

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
