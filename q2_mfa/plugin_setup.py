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
from q2_mfa.types import (
    GroupSummaryFormat,
    MFAResults,
    MFAResultsDirFmt,
    PartialAxesFormat,
    PartialScoresFormat,
)

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

plugin.register_formats(
    GroupSummaryFormat,
    MFAResultsDirFmt,
    PartialAxesFormat,
    PartialScoresFormat,
)
plugin.register_semantic_types(MFAResults)
plugin.register_artifact_class(
    MFAResults,
    directory_format=MFAResultsDirFmt,
    description=(
        "Represents the global MFA ordination together with MFA-specific "
        "partial scores, partial axes, and group summary tables."
    ),
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
    "n_components": Int % Range(1, None),
    "svd_solver": Str % Choices(["full", "randomized"]),
    "random_state": Int,
}

ordination_parameter_descriptions = {
    "n_components": (
        "Number of components to keep. If n_components is not set all "
        "components are kept: n_components == min(n_samples, n_features). "
    ),
    "svd_solver": (
        "SVD solver to use. If full: run exact full SVD using the standard "
        "LAPACK solver and select the components by postprocessing. If  "
        "randomized: run approximate truncated SVD by the method of Halko"
        " et al."
    ),
    "random_state": (
        "Random seed. Used by the randomized solver. Pass an int for "
        "reproducible results across multiple function calls."
    ),
}

plugin.methods.register_function(
    function=pca,
    inputs={"table": FeatureTable[Unconstrained]},
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
    inputs={"feature_tables": Collection[FeatureTable[Unconstrained]]},
    parameters=ordination_parameters,
    outputs=[("mfa_results", MFAResults)],
    input_descriptions={"feature_tables": "A list of feature tables (one per group)."},
    parameter_descriptions=ordination_parameter_descriptions,
    output_descriptions={
        "mfa_results": (
            "MFA results containing the global ordination together with "
            "partial sample coordinates, partial axes summary, and group "
            "summary tables."
        )
    },
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
