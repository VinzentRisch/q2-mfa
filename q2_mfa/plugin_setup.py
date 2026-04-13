# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from q2_types.feature_table import FeatureTable, Frequency, Unconstrained
from q2_types.ordination import PCoAResults
from rachis.core.type import Choices, Collection, Float, Int, Properties, Range, Str
from rachis.plugin import Citations, Plugin

from q2_mfa import __version__, transform_clr
from q2_mfa.mfa import mfa
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
        "replacement_method": Str % Choices("multiplicative", "pseudocount"),
        "delta": Float % Range(0, None, inclusive_start=False),
    },
    outputs=[("transformed_table", FeatureTable[Unconstrained])],
    input_descriptions={"table": "The frequency table."},
    parameter_descriptions={
        "pseudocount": (
            "Value used to replace zeros before CLR. If not provided, a "
            "pseudocount of 1 is used. This parameter is only used when "
            "replacement_method is 'pseudocount'."
        ),
        "replacement_method": (
            "Method used to handle zeros before CLR. 'multiplicative' replaces "
            "zeros while rescaling the remaining values to preserve the "
            "composition. 'pseudocount' adds the pseudocount to all values in "
            "the table."
        ),
        "delta": (
            "Replacement value used for multiplicative replacement. This "
            "parameter is only used when replacement_method is "
            "'multiplicative'."
        ),
    },
    output_descriptions={"transformed_table": "The CLR transformed table."},
    name="Centered log-ratio (CLR) transformation.",
    description=(
        "A centered log-ratio transformation of the input table. The CLR-transformed "
        "table contains real-valued coordinates in Euclidean space, removing the "
        "constant-sum constraint of compositional data. Zeros can be handled "
        "either by additive pseudocount replacement or multiplicative "
        "replacement before the CLR is applied. For more information on the "
        "implementations or the parameters please consult the scikit-bio documentation."
    ),
    citations=[
        citations["martin2003dealing"],
        citations["aitchison1982statistical"],
        citations["aton2025scikit"],
    ],
)

ordination_parameters = {
    "n_components": (
        Int % Range(1, None)
        | Float % Range(0.0, 1.0, inclusive_start=False)
        | Str % Choices(["mle"])
    ),
    "svd_solver": Str % Choices(["auto", "full", "arpack", "randomized"]),
    "tol": Float % Range(0.0, None),
    "iterated_power": Int % Range(0, None) | Str % Choices(["auto"]),
    "n_oversamples": Int % Range(1, None),
    "power_iteration_normalizer": Str % Choices(["auto", "QR", "LU", "none"]),
    "random_state": Int,
}

ordination_parameter_descriptions = {
    "n_components": (
        "Number of components to keep. If n_components is not set all "
        "components are kept: n_components == min(n_samples, n_features). If "
        "n_components == 'mle' and svd_solver == 'full', Minka's MLE is used "
        "to guess the dimension. Use of n_components == 'mle' will interpret "
        "svd_solver == 'auto' as svd_solver == 'full'. If 0 < n_components < "
        "1 and svd_solver == 'full', select the number of components such "
        "that the amount of variance that needs to be explained is greater "
        "than the percentage specified by n_components. If svd_solver == "
        "'arpack', the number of components must be strictly less than the "
        "minimum of n_features and n_samples. Hence, the None case results "
        "in: n_components == min(n_samples, n_features) - 1."
    ),
    "svd_solver": (
        "If auto: the solver is selected by a default policy based on "
        "X.shape and n_components. If the input data is larger than 500x500 "
        "and the number of components to extract is lower than 80% of the "
        "smallest dimension of the data, then the more efficient "
        "'randomized' method is enabled. Otherwise the exact full SVD is "
        "computed and optionally truncated afterwards. If full: run exact "
        "full SVD calling the standard LAPACK solver via scipy.linalg.svd "
        "and select the components by postprocessing. If arpack: run SVD "
        "truncated to n_components calling the ARPACK solver via "
        "scipy.sparse.linalg.svds. It requires strictly 0 < n_components < "
        "min(X.shape). If randomized: run randomized SVD by the method of "
        "Halko et al."
    ),
    "tol": "Tolerance for singular values computed by svd_solver == arpack.",
    "iterated_power": (
        "Number of iterations for the power method computed by svd_solver == "
        "randomized."
    ),
    "n_oversamples": (
        "Additional number of random vectors to sample the range of X when "
        "svd_solver == randomized."
    ),
    "power_iteration_normalizer": (
        "Power iteration normalizer for svd_solver == randomized."
    ),
    "random_state": (
        "Used when the 'arpack' or 'randomized' solvers are used. Pass an int for "
        "reproducible results across multiple function calls"
    ),
}

mfa_parameter_descriptions = {
    **ordination_parameter_descriptions,
    "n_components": (
        f"{ordination_parameter_descriptions['n_components']} This applies only "
        "to the global PCA; the per-group weighting PCAs always use one component "
        "with svd_solver == 'full'."
    ),
    "svd_solver": (
        f"{ordination_parameter_descriptions['svd_solver']} This applies only "
        "to the global PCA; the per-group weighting PCAs always use "
        "svd_solver == 'full' with one component."
    ),
}

plugin.methods.register_function(
    function=pca,
    inputs={"table": FeatureTable[Frequency]},
    parameters=ordination_parameters,
    outputs=[("pca_results", PCoAResults % Properties("pca"))],
    input_descriptions={"table": "The frequency table."},
    parameter_descriptions=ordination_parameter_descriptions,
    output_descriptions={"pca_results": "The PCA results."},
    name="PCA",
    description=(
        "Principal component analysis implementation with scikit-learn. For more "
        "information about the parameters consult the scikit-learn documentation."
    ),
    citations=[
        citations["hotelling1933analysis"],
        citations["pedregosa2011scikit"],
    ],
)

plugin.pipelines.register_function(
    function=mfa,
    inputs={"feature_tables": Collection[FeatureTable[Frequency]]},
    parameters=ordination_parameters,
    outputs=[("mfa_results", PCoAResults % Properties("mfa"))],
    input_descriptions={"feature_tables": "A list of feature tables (one per group)."},
    parameter_descriptions=mfa_parameter_descriptions,
    output_descriptions={"mfa_results": "MFA results."},
    name="Multiple Factor Analysis (MFA)",
    description=(
        "Multiple Factor Analysis (MFA) from multiple feature tables. Each "
        "table is treated as a separate group, and a global PCA is performed "
        "on the concatenated and weighted groups."
    ),
    citations=[
        citations["escofier1994multiple"],
        citations["pedregosa2011scikit"],
    ],
)
