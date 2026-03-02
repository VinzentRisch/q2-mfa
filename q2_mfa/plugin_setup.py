# ----------------------------------------------------------------------------
# Copyright (c) 2026, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from q2_types.feature_table import FeatureTable, Frequency, Unconstrained
from rachis.core.type import Float, Range
from rachis.plugin import Plugin

from q2_mfa import __version__, transform_clr

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
    outputs=[("transformed_table", FeatureTable[Unconstrained])],
    input_descriptions={"table": "The frequency table."},
    parameter_descriptions={
        "pseudocount": "The pseudocount to add to the table before the "
        "transformation. If it is set to None, the pseudocount is "
        "computed as the minimum non-zero value.",
    },
    output_descriptions={"transformed_table": "The CLR transformed table."},
    name="Centered log-ratio (CLR) transformation.",
    description="A centered log-ratio transformation of the input table.",
    citations=[],
)
