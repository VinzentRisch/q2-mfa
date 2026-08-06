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
    """Stores consolidated long-form PLS and DIABLO result tables.

    Each output category is represented by one JSONL table. Block-specific
    rows use an explicit ``block`` field, which keeps PLS and MFA result
    schemas consistent and avoids per-block directory nesting.
    """

    loadings = model.File("loadings.jsonl", format=TableJSONLFileFormat)
    loadings_star = model.File(
        "loadings_star.jsonl", format=TableJSONLFileFormat, optional=True
    )
    variates = model.File("variates.jsonl", format=TableJSONLFileFormat)
    prop_expl_var = model.File("prop_expl_var.jsonl", format=TableJSONLFileFormat)
    vip = model.File("vip.jsonl", format=TableJSONLFileFormat, optional=True)
    ave = model.File("ave.jsonl", format=TableJSONLFileFormat, optional=True)
    crit = model.File("criterion.jsonl", format=TableJSONLFileFormat, optional=True)
    feature_stability = model.File(
        "feature_stability.jsonl", format=TableJSONLFileFormat, optional=True
    )
    auc = model.File("auc.jsonl", format=TableJSONLFileFormat)
    ncomp_selection_weighted_vote_error_rate = model.File(
        "ncomp_selection_weighted_vote_error_rate.jsonl",
        format=TableJSONLFileFormat,
        optional=True,
    )
    final_model_weighted_vote_error_rate = model.File(
        "final_model_weighted_vote_error_rate.jsonl",
        format=TableJSONLFileFormat,
    )
    feature_selection_error_rate = model.File(
        "feature_selection_error_rate.jsonl",
        format=TableJSONLFileFormat,
        optional=True,
    )
