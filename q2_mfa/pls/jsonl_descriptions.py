# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
jsonl_descriptions = {
    "error_rate_weighted": (
        "Cross-validated weighted-vote error-rate means and standard "
        "deviations from mixOmics perf() WeightedVote.error.rate and "
        "WeightedVote.error.rate.sd."
    ),
    "error_rate_majority": (
        "Cross-validated majority-vote error-rate means and standard "
        "deviations from mixOmics perf() MajorityVote.error.rate and "
        "MajorityVote.error.rate.sd."
    ),
    "choice_matrix_weighted": (
        "Component-choice matrix for weighted voting from mixOmics "
        "perf() choice.ncomp$WeightedVote."
    ),
    "choice_matrix_majority": (
        "Component-choice matrix for majority voting from mixOmics "
        "perf() choice.ncomp$MajorityVote."
    ),
    "feature_selection_error_rate": (
        "Cross-validated mean and standard-deviation classification error "
        "rates for every tested keepX combination and component from mixOmics "
        "tune.block.splsda(). Reported error rates use weighted voting when "
        "the weighted parameter is enabled and majority voting otherwise. The "
        "measure parameter determines whether they report overall error rate "
        "(ER) or balanced error rate (BER). The keepx_<block> columns record "
        "the number of features retained for each input block."
    ),
    "feature_selection_selected_features": (
        "Selected keepX feature-count matrix with input blocks as rows and "
        "zero-based components as columns from mixOmics "
        "tune.block.splsda() choice.keepX."
    ),
}
