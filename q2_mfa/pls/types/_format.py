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
    """Stores mixOmics PLS result tables grouped by arbitrary block name."""

    loadings = model.FileCollection(
        r"[^/]+/loadings\.jsonl", format=TableJSONLFileFormat
    )
    loadings_star = model.FileCollection(
        r"[^/]+/loadings_star\.jsonl",
        format=TableJSONLFileFormat,
        optional=True,
    )
    variates = model.FileCollection(
        r"[^/]+/variates\.jsonl", format=TableJSONLFileFormat
    )
    prop_expl_var = model.FileCollection(
        r"[^/]+/prop_expl_var\.jsonl", format=TableJSONLFileFormat
    )
    vip = model.FileCollection(r"[^/]+/vip\.jsonl", format=TableJSONLFileFormat)

    @loadings.set_path_maker
    def _loadings_path(self, block):
        return f"{block}/loadings.jsonl"

    @loadings_star.set_path_maker
    def _loadings_star_path(self, block):
        return f"{block}/loadings_star.jsonl"

    @variates.set_path_maker
    def _variates_path(self, block):
        return f"{block}/variates.jsonl"

    @prop_expl_var.set_path_maker
    def _prop_expl_var_path(self, block):
        return f"{block}/prop_expl_var.jsonl"

    @vip.set_path_maker
    def _vip_path(self, block):
        return f"{block}/vip.jsonl"
