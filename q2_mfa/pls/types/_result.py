# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from dataclasses import dataclass

import pandas as pd


@dataclass
class _PLSFitResult:
    """Holds final mixOmics block sPLS-DA tables before artifact serialization."""

    loadings: dict[str, pd.DataFrame]
    loadings_star: dict[str, pd.DataFrame]
    variates: dict[str, pd.DataFrame]
    prop_expl_var: dict[str, pd.DataFrame]
    vip: dict[str, pd.DataFrame]
    ave: dict[str, pd.DataFrame]
    crit: pd.DataFrame | None
    feature_stability: pd.DataFrame | None
    auc: pd.DataFrame
    error_rate: pd.DataFrame
    feature_component_correlation: pd.DataFrame
    feature_similarity: pd.DataFrame
