# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from q2_types.feature_table import FeatureTable, Frequency, Unconstrained
from rachis import Citations
from rachis.core.type import Choices, Float, Range, Str
from rachis.plugin import Plugin

from q2_mfa import __version__, transform_clr
from q2_mfa.types import (
    GroupSummaryFormat,
    MFAResults,
    MFAResultsDirFmt,
    PartialAxesFormat,
    PrinceWideTSVFormat,
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
    PrinceWideTSVFormat,
)
plugin.register_semantic_types(MFAResults)
plugin.register_artifact_class(
    MFAResults,
    directory_format=MFAResultsDirFmt,
    description=(
        "Represents the global MFA ordination together with MFA-specific "
        "Prince-style sample, feature, partial axes, and group summary tables."
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
