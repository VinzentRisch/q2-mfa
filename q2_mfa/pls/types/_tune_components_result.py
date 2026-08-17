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

    error_rate: pd.DataFrame
    choice_matrix: pd.DataFrame
