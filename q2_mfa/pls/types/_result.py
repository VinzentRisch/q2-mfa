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
class _PLSTuneComponentsResult:
    """Holds DIABLO component-selection results before serialization."""

    error_rate_weighted: pd.DataFrame
    error_rate_majority: pd.DataFrame
    choice_matrix_weighted: pd.DataFrame
    choice_matrix_majority: pd.DataFrame
