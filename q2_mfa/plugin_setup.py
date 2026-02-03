# ----------------------------------------------------------------------------
# Copyright (c) 2026, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from q2_types.feature_table import Composition, FeatureTable, Frequency
from rachis import Citations
from rachis.core.type import Bool, Float, Range
from rachis.plugin import Plugin

from q2_mfa import __version__, transform_clr

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
        "pseudocount_data_adaptive": Bool,
    },
    outputs=[("clr_table", FeatureTable[Composition])],
    input_descriptions={"table": "The frequency table."},
    parameter_descriptions={
        "pseudocount": "The pseudocount to add to the table before the transformation.",
        "pseudocount_data_adaptive": "The pseudocount is set to the minimal non-zero "
        "value in the feature table.",
    },
    output_descriptions={"clr_table": "The CLR transformed table."},
    name="Centered log-ratio (CLR) transformation.",
    description="A centered log-ratio transformation of the input table.",
    citations=[],
)
