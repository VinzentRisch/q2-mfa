# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import rachis.plugin.model as model
from q2_types.tabular import TableJSONLFileFormat


class PLSAnalysisDirFmt(model.DirectoryFormat):
    """Stores mixOmics PLS result tables grouped by output and block name.

    Block-specific tables are stored under a directory named for the output,
    with one JSONL table named after each data block. DIABLO-only diagnostics
    are optional: ``ave`` contains the inner, outer, and block-specific AVE
    tables, and ``crit`` contains the combined convergence-criterion table.
    """

    loadings = model.FileCollection(
        r"loadings/[^/]+\.jsonl", format=TableJSONLFileFormat
    )
    loadings_star = model.FileCollection(
        r"loadings_star/[^/]+\.jsonl",
        format=TableJSONLFileFormat,
        optional=True,
    )
    variates = model.FileCollection(
        r"variates/[^/]+\.jsonl", format=TableJSONLFileFormat
    )
    prop_expl_var = model.FileCollection(
        r"prop_expl_var/[^/]+\.jsonl", format=TableJSONLFileFormat
    )
    vip = model.FileCollection(
        r"vip/[^/]+\.jsonl", format=TableJSONLFileFormat, optional=True
    )
    ave = model.FileCollection(
        r"ave/[^/]+\.jsonl", format=TableJSONLFileFormat, optional=True
    )
    crit = model.FileCollection(
        r"crit/criterion\.jsonl", format=TableJSONLFileFormat, optional=True
    )

    @loadings.set_path_maker
    def _loadings_path(self, block):
        return f"loadings/{block}.jsonl"

    @loadings_star.set_path_maker
    def _loadings_star_path(self, block):
        return f"loadings_star/{block}.jsonl"

    @variates.set_path_maker
    def _variates_path(self, block):
        return f"variates/{block}.jsonl"

    @prop_expl_var.set_path_maker
    def _prop_expl_var_path(self, block):
        return f"prop_expl_var/{block}.jsonl"

    @vip.set_path_maker
    def _vip_path(self, block):
        return f"vip/{block}.jsonl"

    @ave.set_path_maker
    def _ave_path(self, table):
        return f"ave/{table}.jsonl"

    @crit.set_path_maker
    def _crit_path(self):
        return "crit/criterion.jsonl"
