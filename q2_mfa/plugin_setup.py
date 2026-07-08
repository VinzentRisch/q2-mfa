# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from q2_types.feature_table import FeatureTable, Frequency, Unconstrained
from rachis import Citations, MetadataColumn
from rachis.core.type import Choices, Float, Range, Str
from rachis.plugin import Bool, Categorical, Int, Plugin

from q2_mfa import __version__, pretreat_metabolome, transform_clr

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
    function=pretreat_metabolome,
    inputs={"table": FeatureTable[Unconstrained]},
    parameters={
        "sample_normalization": Str % Choices(["pqn"]),
        "pqn_method": Str % Choices(["median", "mean"]),
        "pqn_ref_samples": MetadataColumn[Categorical],
        "pqn_ref_label": Str,
        "transform": Str % Choices(["log", "log10", "sqrt"]),
        "pseudocount": Float % Range(0, None, inclusive_start=False),
        "center": Bool,
        "scale": Str % Choices(["auto", "pareto", "range"]),
        "impute": Str % Choices(["knn", "rf"]),
        "knn_neighbors": Int % Range(1, None),
        "rf_n_estimators": Int % Range(1, None),
        "rf_random_state": Int,
    },
    outputs=[("pretreated_table", FeatureTable[Unconstrained])],
    input_descriptions={"table": "Metabolomics feature table."},
    parameter_descriptions={
        "sample_normalization": (
            "Sample-level normalization to apply: 'pqn' "
            "(Probabilistic Quotient Normalization)."
        ),
        "pqn_method": (
            "How to construct the PQN reference spectrum: 'median' or 'mean'."
        ),
        "pqn_ref_samples": (
            "Categorical metadata column name used to select samples "
            "for building the PQN reference spectrum."
        ),
        "pqn_ref_label": (
            "Label value in `pqn_ref_samples` indicating which samples to use "
            "for the PQN reference. Required when `pqn_ref_samples` is provided."
        ),
        "transform": "Transformation applied to the data ('log', 'log10', 'sqrt').",
        "pseudocount": (
            "Offset added before log transform. If omitted/None and transform='log', "
            "it is inferred as the minimum non-zero value."
        ),
        "center": "If True, mean-center each feature",
        "scale": (
            "Feature scaling method applied: 'auto' (mean-center and divide by std), "
            "'pareto' (mean-center and divide by sqrt(std)), or 'range' (mean-center "
            "and divide by max-min)."
        ),
        "impute": (
            "Missing-value imputation method. K-Nearest Neighbors imputation, or "
            "Random Forest imputation."
        ),
        "knn_neighbors": "Number of neighbors for KNN imputation.",
        "rf_n_estimators": "Number of trees for RandomForest imputation.",
        "rf_random_state": "Random state for RandomForest reproducibility.",
    },
    output_descriptions={
        "pretreated_table": (
            "Pretreated table after optional imputation, normalization, "
            "transformation, centering, and scaling."
        )
    },
    name="Metabolomics pretreatment",
    description=(
        "Applies metabolomics-friendly pretreatment in order: imputation,  sample "
        "normalization, transformation, centering, and feature scaling."
    ),
    citations=[],
)
