# ----------------------------------------------------------------------------
# Copyright (c) 2026, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from q2_types.feature_table import Composition, FeatureTable, Frequency
from q2_types.ordination import PCoAResults
from rachis.core.type import Choices, Float, Int, Properties, Range, Str
from rachis.plugin import Citations, Plugin

from q2_mfa import __version__, transform_clr
from q2_mfa.pca import pca

citations = Citations.load("citations.bib", package="q2_mfa")

plugin = Plugin(
    name="mfa",
    version=__version__,
    website="https://github.com/bokulich-lab/q2-mfa",
    package="q2_mfa",
    description="A QIIME 2 plugin for PCA and MFA analysis.",
    short_description="PCA and MFA analysis",
    citations=[],
)

plugin.methods.register_function(
    function=transform_clr,
    inputs={"table": FeatureTable[Frequency]},
    parameters={
        "pseudocount": Float % Range(0, None, inclusive_start=False),
    },
    outputs=[("clr_table", FeatureTable[Composition])],
    input_descriptions={"table": "The frequency table."},
    parameter_descriptions={
        "pseudocount": "The pseudocount to add to the table before the "
        "transformation. If it is set to None, the pseudocount is "
        "computed as the minimum non-zero value.",
    },
    output_descriptions={"clr_table": "The CLR transformed table."},
    name="Centered log-ratio (CLR) transformation.",
    description="A centered log-ratio transformation of the input table.",
    citations=[],
)

plugin.methods.register_function(
    function=pca,
    inputs={"table": FeatureTable[Frequency]},
    parameters={
        "n_components": (
            Int % Range(1, None)
            | Float % Range(0.0, 1.0, inclusive_start=False)
            | Str % Choices(["mle"])
        ),
        "svd_solver": Str
        % Choices(["auto", "full", "covariance_eigh", "arpack", "randomized"]),
        "tol": Float % Range(0.0, None),
        "iterated_power": Int % Range(0, None) | Str % Choices(["auto"]),
        "n_oversamples": Int % Range(1, None),
        "power_iteration_normalizer": Str % Choices(["auto", "QR", "LU", "none"]),
        "random_state": Int,
    },
    outputs=[("pca_results", PCoAResults % Properties("pca"))],
    input_descriptions={"table": "The frequency table."},
    parameter_descriptions={
        "n_components": "Number of components to keep. An integer keeps that "
        "many components, a float in (0, 1) keeps enough components to "
        "explain that fraction of the variance, 'mle' estimates the "
        "dimensionality automatically using Minka's Maximum Likelihood "
        "Estimation, and if not set all components are kept.",
        "svd_solver": "Solver to use. auto selects a solver based on X.shape "
        "and n_components: if the input data has fewer than 1000 features and "
        "more than 10 times as many samples, then covariance_eigh is used. "
        "Otherwise, if the input data is larger than 500 by 500 and the "
        "number of components to extract is lower than 80% of the smallest "
        "dimension of the data, then randomized is selected. Otherwise, the "
        "exact full SVD is computed and optionally truncated afterwards.",
        "tol": "Tolerance for singular values computed by svd_solver == " "arpack.",
        "iterated_power": "Number of iterations for the power method "
        "computed by svd_solver == randomized.",
        "n_oversamples": "Additional number of random vectors to sample the "
        "range of X when svd_solver == randomized.",
        "power_iteration_normalizer": "Power iteration normalizer for the "
        "randomized SVD solver.",
        "random_state": "Controls the randomness when the arpack or "
        "randomized solvers are used.",
    },
    output_descriptions={"pca_results": "The PCA results."},
    name="PCA",
    description="Linear dimensionality reduction using Singular Value "
    "Decomposition of the data to project it to a lower dimensional space. "
    "The input data is centered but not scaled for each feature before "
    "applying the SVD.",
    citations=[citations["hotelling1933analysis"]],
)
