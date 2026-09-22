# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
# ----------------------------------------------------------------------------
from rachis.plugin.testing import TestPluginBase

from q2_mfa.pls import (
    AssociationMatrix,
    AssociationMatrixDirFmt,
    PLSTuneComponents,
    PLSTuneComponentsDirFmt,
)


class TestPLSTypes(TestPluginBase):
    package = "q2_mfa.pls.types.tests"

    def test_tune_components_semantic_type_registration(self):
        self.assertRegisteredSemanticType(PLSTuneComponents)

    def test_tune_components_semantic_type_to_format_registration(self):
        self.assertSemanticTypeRegisteredToFormat(
            PLSTuneComponents, PLSTuneComponentsDirFmt
        )

    def test_association_matrix_semantic_type_registration(self):
        self.assertRegisteredSemanticType(AssociationMatrix)

    def test_association_matrix_semantic_type_to_format_registration(self):
        self.assertSemanticTypeRegisteredToFormat(
            AssociationMatrix, AssociationMatrixDirFmt
        )
