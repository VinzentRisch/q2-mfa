# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from rachis.plugin.testing import TestPluginBase

from q2_mfa.types import MFAResults, MFAResultsDirFmt


class TestMFATypes(TestPluginBase):
    package = "q2_mfa.types.tests"

    def test_mfa_results_semantic_type_registration(self):
        self.assertRegisteredSemanticType(MFAResults)

    def test_mfa_results_semantic_type_to_format_registration(self):
        self.assertSemanticTypeRegisteredToFormat(MFAResults, MFAResultsDirFmt)
