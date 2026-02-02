# ----------------------------------------------------------------------------
# Copyright (c) 2024, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from qiime2.plugin import Citations, Plugin
from mfa import __version__

citations = Citations.load("citations.bib", package="mfa")

plugin = Plugin(
    name="q2_mfa",
    version=__version__,
    website="https://github.com/bokulich-lab/q2-mfa",
    package="mfa",
    description="A QIIME 2 plugin for PCA and MFA analysis.",
    short_description="PCA and MFA analysis",
    citations=[]
)
