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
    PLSTuneComponents,
    PLSTuneComponentsDirFmt,
    tune_components_block_splsda,
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

plugin.methods.register_function(
    function=tune_components_block_splsda,
    inputs={"tables": Collection[FeatureTable[Unconstrained]]},
    parameters={
        "y": MetadataColumn[Categorical],
        "design_matrix": Metadata,
        "design_weight": Float % Range(0, 1),
        "ncomp": Int % Range(2, None),
        "scale": Bool,
        "tol": Float % Range(0, None, inclusive_start=False),
        "max_iter": Int % Range(1, None),
        "near_zero_var": Bool,
        "validation": Str % Choices("Mfold", "loo"),
        "folds": Int % Range(2, None),
        "nrepeat": Int % Range(3, None),
        "signif_threshold": Float % Range(0, 1),
        "seed": Int % Range(0, 2**31 - 1),
        "threads": Threads,
    },
    outputs=[("tuning", PLSTuneComponents)],
    input_descriptions={"tables": "Named feature tables used as DIABLO blocks."},
    parameter_descriptions={
        "y": "Categorical class labels for the input samples.",
        "design_matrix": "Optional DIABLO block-design matrix metadata.",
        "design_weight": "Optional scalar DIABLO block-design weight.",
        "ncomp": "Maximum number of components to evaluate.",
        "scale": "Whether to scale features within each block.",
        "tol": "Convergence tolerance for the dense DIABLO fit.",
        "max_iter": "Maximum number of iterations for the dense DIABLO fit.",
        "near_zero_var": "Whether mixOmics removes near-zero variance features.",
        "validation": "Cross-validation strategy used by mixOmics perf.",
        "folds": "Number of folds for M-fold cross-validation.",
        "nrepeat": "Number of cross-validation repeats.",
        "signif_threshold": "Minimum component improvement required by perf.",
        "seed": "Random seed for mixOmics cross-validation.",
        "threads": (
            "Number of BiocParallel workers. Use 0 or 'auto' to use "
            "BiocParallel's default."
        ),
    },
    output_descriptions={
        "tuning": "DIABLO weighted and majority-vote component-tuning tables."
    },
    name="Tune DIABLO block PLS-DA components",
    description=(
        "Fits DIABLO models across component counts and reports cross-validated "
        "weighted-vote error rates."
    ),
)

plugin.register_formats(
    ComponentAnalysisDirFmt,
    PLSTuneComponentsDirFmt,
)
plugin.register_semantic_types(
    ComponentAnalysis,
    PLSTuneComponents,
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
    PLSTuneComponents,
    directory_format=PLSTuneComponentsDirFmt,
    description="Represents PLS component-selection results produced by mixOmics.",
)

importlib.import_module("q2_mfa.component_analysis.types._transformer")
importlib.import_module("q2_mfa.pls.types._tune_components_transformer")
