# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import PLSFit, PLSFitDirFmt, PLSTune, PLSTuneDirFmt


class TestPLSTypes(TestPluginBase):
    package = "q2_mfa.pls.types.tests"

    def test_pls_fit_semantic_type_registration(self):
        self.assertRegisteredSemanticType(PLSFit)

    def test_pls_fit_semantic_type_to_format_registration(self):
        self.assertSemanticTypeRegisteredToFormat(PLSFit, PLSFitDirFmt)

    def test_pls_tune_semantic_type_registration(self):
        self.assertRegisteredSemanticType(PLSTune)

    def test_pls_tune_semantic_type_to_format_registration(self):
        self.assertSemanticTypeRegisteredToFormat(PLSTune, PLSTuneDirFmt)
