# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
tune_components_descriptions = {
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
}


feature_selection_descriptions = {
    "error_rate": (
        "Cross-validated mean and standard-deviation classification error "
        "rates for every tested keepX combination and component from mixOmics "
        "tune.block.splsda(). Reported error rates use weighted voting when "
        "the weighted parameter is enabled and majority voting otherwise. The "
        "measure parameter determines whether they report overall error rate "
        "(ER) or balanced error rate (BER). The keepx_<block> columns record "
        "the number of features retained for each input block."
    ),
    "selected_features": (
        "Selected keepX feature-count matrix with one-based components as "
        "rows and input blocks as columns from mixOmics "
        "tune.block.splsda() choice.keepX."
    ),
}


fit_descriptions = {
    "loadings": (
        "Per-feature component loading weights from mixOmics block.splsda() "
        "model$loadings, with input-block and component labels."
    ),
    "loadings_star": (
        "Per-feature deflated component loading weights from mixOmics "
        "block.splsda() model$loadings.star, with input-block and component "
        "labels."
    ),
    "variates": (
        "Per-sample latent-component scores from mixOmics block.splsda() "
        "model$variates, with input-block and component labels."
    ),
    "prop_expl_var": (
        "Proportion of explained variance per input block and latent component "
        "from mixOmics block.splsda() model$prop_expl_var."
    ),
    "vip": (
        "Variable importance in projection scores from mixOmics block.splsda() "
        "for each input block, feature, and component."
    ),
    "ave": (
        "Average variance explained summaries from mixOmics block.splsda() "
        "model$AVE, with metric, block, and component labels."
    ),
    "crit": (
        "Per-component convergence criterion traces from mixOmics block.splsda() "
        "model$crit."
    ),
    "feature_stability": (
        "Mean cross-validation feature-selection frequencies from mixOmics "
        "perf() features$stable, grouped by block, feature, and component."
    ),
    "auc": (
        "Per-component contrast AUC values and p-values from mixOmics perf() "
        "with auc enabled."
    ),
    "error_rate_weighted": (
        "Cross-validated weighted-vote classification error-rate means and "
        "standard deviations from mixOmics perf() WeightedVote.error.rate and "
        "WeightedVote.error.rate.sd."
    ),
    "error_rate_majority": (
        "Cross-validated majority-vote classification error-rate means and "
        "standard deviations from mixOmics perf() MajorityVote.error.rate and "
        "MajorityVote.error.rate.sd."
    ),
    "feature_component_correlation": (
        "Correlations between selected input features and their own-block latent "
        "component variates."
    ),
    "feature_similarity": (
        "Pairwise selected-feature similarities across all fitted components from "
        "mixOmics circosPlot()."
    ),
}
