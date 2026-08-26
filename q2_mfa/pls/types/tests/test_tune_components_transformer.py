# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
# ----------------------------------------------------------------------------
import json

import pandas as pd
import qiime2
from rachis.plugin.testing import TestPluginBase
from rachis.plugin.util import transform

from q2_mfa.pls import PLSTuneComponentsDirFmt
from q2_mfa.pls.types._result import _PLSTuneComponentsResult


class TestPLSTuneComponentsTransformer(TestPluginBase):
    package = "q2_mfa.pls.types.tests"

    def test_writes_jsonl_with_framework_transformer(self):
        result = _PLSTuneComponentsResult(
            error_rate_weighted=pd.DataFrame(
                {
                    "distance": ["max.dist"],
                    "class": ["Overall.BER"],
                    "component": [0],
                    "mean": [0.24],
                    "sd": [0.01],
                }
            ),
            error_rate_majority=pd.DataFrame(
                {
                    "distance": ["max.dist"],
                    "class": ["Overall.BER"],
                    "component": [0],
                    "mean": [0.26],
                    "sd": [0.02],
                }
            ),
            choice_matrix_weighted=pd.DataFrame(
                {"max.dist": [2]}, index=pd.Index(["Overall.BER"], name="id")
            ),
            choice_matrix_majority=pd.DataFrame(
                {"max.dist": [2]}, index=pd.Index(["Overall.BER"], name="id")
            ),
        )

        directory_format = transform(result, to_type=PLSTuneComponentsDirFmt)

        directory_format.validate()
        with directory_format.error_rate_weighted.path_maker().open() as fh:
            error_rate_header = json.loads(next(fh))
        with directory_format.choice_matrix_weighted.path_maker().open() as fh:
            choice_matrix_header = json.loads(next(fh))
        self.assertEqual(error_rate_header["index"], [])
        self.assertEqual(
            error_rate_header["description"],
            "Cross-validated DIABLO weighted-vote error-rate means and standard "
            "deviations from mixOmics perf() WeightedVote.error.rate and "
            "WeightedVote.error.rate.sd.",
        )
        self.assertEqual(
            choice_matrix_header["description"],
            "DIABLO component-choice matrix for weighted voting from mixOmics "
            "perf() choice.ncomp$WeightedVote.",
        )

        expected = result.error_rate_weighted.copy()
        expected.insert(0, "id", ["row1"])
        pd.testing.assert_frame_equal(
            directory_format.error_rate_weighted.view(pd.DataFrame),
            expected,
            check_dtype=False,
        )

        metadata = directory_format.error_rate_weighted.view(qiime2.Metadata)
        self.assertEqual(metadata.id_count, 1)
        self.assertEqual(list(metadata.ids), ["row1"])
        self.assertNotIn("id", metadata.to_dataframe().columns)
