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
class _PLSFeatureSelectionResult:
    error_rate: pd.DataFrame
    selected_features: pd.DataFrame
