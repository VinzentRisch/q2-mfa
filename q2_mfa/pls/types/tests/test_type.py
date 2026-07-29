# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import PLSAnalysis, PLSAnalysisDirFmt


class TestPLSTypes(TestPluginBase):
    package = "q2_mfa.pls.types.tests"

    def test_pls_analysis_semantic_type_registration(self):
        self.assertRegisteredSemanticType(PLSAnalysis)

    def test_pls_analysis_semantic_type_to_format_registration(self):
        self.assertSemanticTypeRegisteredToFormat(PLSAnalysis, PLSAnalysisDirFmt)
