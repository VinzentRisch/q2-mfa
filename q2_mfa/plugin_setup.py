# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from q2_types.feature_table import FeatureTable, Frequency, Unconstrained
from q2_types.ordination import PCoAResults
from rachis.core.type import Bool, Choices, Float, Int, Properties, Range, Str
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

plugin.methods.register_function(
    function=pca,
    inputs={"table": FeatureTable[Unconstrained]},
    parameters={
        "rescale_with_mean": Bool,
        "rescale_with_std": Bool,
        "n_components": Int % Range(1, None),
        "n_iter": Int % Range(0, None),
        "random_state": Int,
        "engine": Str % Choices(["sklearn", "scipy"]),
    },
    outputs=[("pca_results", PCoAResults % Properties("pca"))],
    input_descriptions={"table": "The frequency table."},
    parameter_descriptions={
        "n_components": "Number of principal components to compute.",
        "rescale_with_mean": (
            "Whether to center each feature by subtracting its mean before "
            "performing SVD."
        ),
        "rescale_with_std": (
            "Whether to standardize each feature to unit variance before "
            "performing SVD."
        ),
        "n_iter": (
            "Number of iterations used by the 'sklearn' randomized SVD "
            "engine. This parameter is ignored by the 'scipy' engine."
        ),
        "engine": (
            "SVD engine used by prince. 'sklearn' uses randomized SVD, 'scipy' "
            "uses SciPy SVD."
        ),
        "random_state": (
            "Random seed used by the 'sklearn' SVD engine. Pass an int for "
            "reproducible results across multiple function calls. This "
            "parameter is ignored by the 'scipy' engine."
        ),
    },
    output_descriptions={"pca_results": "The PCA results."},
    name="PCA",
    description=(
        "Principal component analysis implementation with the 'prince' package. "
        "The output is an ordination result: eigenvalues correspond to prince "
        "eigenvalues, sites correspond to sample scores, species correspond to "
        "feature coordinates, and proportion explained corresponds to prince "
        "percentage of variance."
    ),
    citations=[
        citations["Halford_Prince"],
    ],
)
