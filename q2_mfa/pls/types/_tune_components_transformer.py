# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd

from q2_mfa.plugin_setup import plugin

from ._format import PLSTuneComponentsDirFmt
from ._result import _PLSTuneComponentsResult


@plugin.register_transformer
def _tune_components_to_dirfmt(
    result: _PLSTuneComponentsResult,
) -> PLSTuneComponentsDirFmt:
    """Serializes DIABLO component-selection tables as Table JSONL."""
    directory_format = PLSTuneComponentsDirFmt()

    error_rate_weighted = result.error_rate_weighted.copy()
    error_rate_majority = result.error_rate_majority.copy()
    choice_matrix_weighted = result.choice_matrix_weighted.reset_index()
    choice_matrix_majority = result.choice_matrix_majority.reset_index()

    error_rate_weighted.insert(
        0, "id", [f"row{index}" for index in range(1, len(error_rate_weighted) + 1)]
    )
    error_rate_majority.insert(
        0, "id", [f"row{index}" for index in range(1, len(error_rate_majority) + 1)]
    )

    error_rate_weighted.attrs["description"] = (
        "Cross-validated DIABLO weighted-vote error-rate means and standard "
        "deviations from mixOmics perf() WeightedVote.error.rate and "
        "WeightedVote.error.rate.sd."
    )
    error_rate_majority.attrs["description"] = (
        "Cross-validated DIABLO majority-vote error-rate means and standard "
        "deviations from mixOmics perf() MajorityVote.error.rate and "
        "MajorityVote.error.rate.sd."
    )
    choice_matrix_weighted.attrs["description"] = (
        "DIABLO component-choice matrix for weighted voting from mixOmics "
        "perf() choice.ncomp$WeightedVote."
    )
    choice_matrix_majority.attrs["description"] = (
        "DIABLO component-choice matrix for majority voting from mixOmics "
        "perf() choice.ncomp$MajorityVote."
    )

    directory_format.error_rate_weighted.write_data(error_rate_weighted, pd.DataFrame)
    directory_format.error_rate_majority.write_data(error_rate_majority, pd.DataFrame)
    directory_format.choice_matrix_weighted.write_data(
        choice_matrix_weighted, pd.DataFrame
    )
    directory_format.choice_matrix_majority.write_data(
        choice_matrix_majority, pd.DataFrame
    )
    return directory_format
