# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import importlib

from q2_types.feature_table import FeatureTable, Frequency, Unconstrained
from rachis import Citations
from rachis.core.type import (
    Bool,
    Categorical,
    Choices,
    Collection,
    Float,
    Int,
    Metadata,
    MetadataColumn,
    Range,
    Str,
)
from rachis.plugin import Plugin, Threads

from q2_mfa import __version__
from q2_mfa.component_analysis import ComponentAnalysis, ComponentAnalysisDirFmt
from q2_mfa.pls import (
    PLSFeatureSelection,
    PLSFeatureSelectionDirFmt,
    PLSFit,
    PLSFitDirFmt,
    PLSTuneComponents,
    PLSTuneComponentsDirFmt,
    fit_block_splsda,
)
from q2_mfa.preprocessing import transform_clr

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

fit_block_splsda_parameters = {
    "y": MetadataColumn[Categorical],
    "design_matrix": Metadata,
    "design_weight": Float % Range(0, 1),
    "ncomp": Int % Range(1, None),
    "keepx": Collection[Str],
    "scale": Bool,
    "tol": Float % Range(0, None, inclusive_start=False),
    "max_iter": Int % Range(1, None),
    "near_zero_var": Bool,
    "validation": Str % Choices("Mfold", "loo"),
    "folds": Int % Range(2, None),
    "nrepeat": Int % Range(3, None),
    "signif_threshold": Float % Range(0, 1),
    "distance": Str % Choices("max.dist", "centroids.dist", "mahalanobis.dist"),
    "measure": Str % Choices("overall", "BER"),
    "weighted": Bool,
    "seed": Int % Range(0, 2**31 - 1),
    "threads": Threads,
}

fit_block_splsda_parameter_descriptions = {
    "y": "Categorical metadata column used as the DIABLO classification target.",
    "design_matrix": (
        "Optional Metadata-encoded block design matrix. Use either this input "
        "or design-weight, but not both."
    ),
    "design_weight": (
        "Optional scalar design weight passed directly to mixOmics. Use either "
        "this parameter or design-matrix."
    ),
    "ncomp": "Manual component count. Provide this value or tuned_components.",
    "keepx": (
        "One comma-separated feature-count string for each component, in "
        "component order. Values within a string follow input block order."
    ),
    "scale": "Whether feature blocks are scaled for the final fit.",
    "tol": "Convergence tolerance used by the final fit.",
    "max_iter": "Maximum iterations used by the final fit.",
    "near_zero_var": ("Whether the final fit removes near-zero variance features."),
    "validation": "Cross-validation scheme used for final-model perf.",
    "folds": "Number of folds used for final-model perf.",
    "nrepeat": "Number of repeats used for final-model perf.",
    "signif_threshold": "Significance threshold used by final-model perf.",
    "distance": "Prediction distance used with tuned_components.",
    "measure": "Error measure used with tuned_components.",
    "weighted": "Whether to use the weighted component-choice matrix.",
    "seed": "Captured random seed used by final-model perf and parallel workers.",
    "threads": (
        "Number of parallel workers used by final-model perf. Use 0 or 'auto' "
        "to use BiocParallel's default. One thread uses BiocParallel "
        "SerialParam on every operating system. With more than one thread, "
        "macOS and Linux use MulticoreParam and Windows uses SnowParam with "
        "SOCK workers."
    ),
}

plugin.methods.register_function(
    function=fit_block_splsda,
    inputs={
        "tables": Collection[FeatureTable[Unconstrained]],
        "tuned_components": PLSTuneComponents,
        "feature_selection": PLSFeatureSelection,
    },
    parameters=fit_block_splsda_parameters,
    outputs=[("pls_results", PLSFit)],
    input_descriptions={
        "tables": "Named unconstrained feature tables used as DIABLO blocks.",
        "tuned_components": "Optional artifact used to determine ncomp.",
        "feature_selection": "Optional artifact supplying selected keepX values.",
    },
    parameter_descriptions=fit_block_splsda_parameter_descriptions,
    output_descriptions={"pls_results": "Final DIABLO block sPLS-DA output tables."},
    name="Fit DIABLO block sparse PLS-DA",
    description=(
        "Fits a mixOmics block.splsda model, also known as DIABLO, from "
        "supplied or previously selected components and retained feature counts."
    ),
    citations=[citations["rohart2017mixomics"], citations["singh2019diablo"]],
)

plugin.register_formats(
    ComponentAnalysisDirFmt,
    PLSFitDirFmt,
    PLSTuneComponentsDirFmt,
    PLSFeatureSelectionDirFmt,
)
plugin.register_semantic_types(
    ComponentAnalysis, PLSFit, PLSTuneComponents, PLSFeatureSelection
)
plugin.register_artifact_class(
    ComponentAnalysis,
    directory_format=ComponentAnalysisDirFmt,
    description=(
        "Represents the output for PCA and MFA actions implemented with the Prince "
        "package."
    ),
)
plugin.register_artifact_class(
    PLSFit,
    directory_format=PLSFitDirFmt,
    description="Represents fitted PLS model result tables produced by mixOmics.",
)
plugin.register_artifact_class(
    PLSTuneComponents,
    directory_format=PLSTuneComponentsDirFmt,
    description="Represents PLS component-selection results produced by mixOmics.",
)
plugin.register_artifact_class(
    PLSFeatureSelection,
    directory_format=PLSFeatureSelectionDirFmt,
    description="Represents PLS feature-selection results produced by mixOmics.",
)

importlib.import_module("q2_mfa.component_analysis.types._transformer")
importlib.import_module("q2_mfa.pls.types._transformer")
