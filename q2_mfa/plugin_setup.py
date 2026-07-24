# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import importlib

from q2_types.feature_table import FeatureTable, Frequency, Unconstrained
from rachis.core.type import Bool, Choices, Collection, Float, Int, Metadata, Range, Str
from rachis.plugin import Citations, Plugin

from q2_mfa import __version__, transform_clr
from q2_mfa.mfa import mfa
from q2_mfa.pca import pca
from q2_mfa.types import ComponentAnalysis, ComponentAnalysisDirFmt

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
    "rescale_with_mean": Bool,
    "rescale_with_std": Bool,
    "n_components": Int % Range(2, None),
    "n_iter": Int % Range(0, None),
    "random_state": Int,
    "engine": Str % Choices(["sklearn", "scipy"]),
    "filter_zero_variance": Bool,
}

ordination_parameter_descriptions = {
    "n_components": "Number of principal components to compute.",
    "rescale_with_mean": (
        "Whether to center each feature by subtracting its mean before "
        "performing SVD. "
    ),
    "rescale_with_std": (
        "Whether to standardize each feature to unit variance before " "performing SVD."
    ),
    "n_iter": (
        "Number of iterations used by the 'sklearn' randomized SVD "
        "engine. This parameter is ignored by the 'scipy' engine.  "
    ),
    "engine": (
        "SVD engine used by prince. 'sklearn' uses randomized SVD, 'scipy'"
        " uses SciPy SVD."
    ),
    "random_state": (
        "Random seedused by the 'sklearn' SVD engine. Pass an int for "
        "reproducible results across multiple function calls.This "
        "parameter is ignored by the 'scipy' engine."
    ),
    "filter_zero_variance": (
        "Whether to remove columns with zero variance before ordination."
    ),
}

mfa_parameters = {
    **ordination_parameters,
    "sample_metadata": Metadata,
    "metadata_groups": Collection[Str],
}

mfa_parameter_descriptions = {
    **ordination_parameter_descriptions,
    "sample_metadata": (
        "Optional sample metadata to include as additional MFA groups."
    ),
    "metadata_groups": (
        "Optional mapping from metadata group names to comma-separated metadata "
        "column strings. Pass a collection/dict such as "
        "{'group': 'column1,column2'} to define explicit groups. If only a "
        "string is provided, all metadata columns are included in a group with "
        "that string as the group name. If sample metadata is provided without "
        "this parameter, all metadata columns are included in a group named "
        "'metadata'. Groups must contain only numeric or only categorical columns."
    ),
}

plugin.methods.register_function(
    function=pca,
    inputs={"table": FeatureTable[Unconstrained]},
    parameters=ordination_parameters,
    outputs=[("pca_results", ComponentAnalysis)],
    input_descriptions={"table": "The frequency table."},
    parameter_descriptions=ordination_parameter_descriptions,
    output_descriptions={"pca_results": "The PCA results."},
    name="PCA",
    description=(
        "Principal component analysis implementation with the prince package. "
        "The output is a component-analysis result containing eigenvalues, "
        "sample coordinates, feature coordinates, variance percentages, and "
        "supporting PCA tables from prince. The result can also be viewed as an "
        "ordination result through the registered transformer. Features with "
        "missing values are automatically removed before analysis. Please check "
        "the prince package docs for more information:"
        "https://maxhalford.github.io/prince/pca/"
    ),
    citations=[
        citations["Halford_Prince"],
    ],
)

plugin.methods.register_function(
    function=mfa,
    inputs={"tables": Collection[FeatureTable[Unconstrained]]},
    parameters=mfa_parameters,
    outputs=[("mfa_results", ComponentAnalysis)],
    input_descriptions={
        "tables": (
            "Optional feature tables to include as MFA groups. At least two "
            "groups must be provided across feature tables and sample metadata "
            "groups."
        )
    },
    parameter_descriptions=mfa_parameter_descriptions,
    output_descriptions={"mfa_results": "MFA results"},
    name="Multiple Factor Analysis (MFA)",
    description=(
        "Multiple Factor Analysis (MFA) from multiple feature tables. Each "
        "table is treated as a separate group, and the analysis is performed "
        "with the prince python package."
        "The output is an ordination result: eigenvalues correspond to prince "
        "eigenvalues, sites correspond to sample coordinates, species correspond to "
        "feature coordinates, and proportion explained corresponds to prince "
        "percentage of variance. All other outputs come directly from the prince "
        "package. Please check the prince package docs for more information:"
        "https://maxhalford.github.io/prince/mfa/"
    ),
    citations=[
        citations["escofier1994multiple"],
        citations["Halford_Prince"],
    ],
)

plugin.register_formats(
    ComponentAnalysisDirFmt,
)
plugin.register_semantic_types(ComponentAnalysis)
plugin.register_artifact_class(
    ComponentAnalysis,
    directory_format=ComponentAnalysisDirFmt,
    description=(
        "Represents the output for PCA and MFA actions implemented with the Prince "
        "package."
    ),
)

importlib.import_module("q2_mfa.types._transformer")
