# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import importlib

import numpy as np
import pandas as pd


class _FakeArray:
    def __array__(self, dtype=None):
        return np.asarray([[2], [1]], dtype=dtype)


class _FakeChoice:
    def rx2(self, name):
        assert name in {"WeightedVote", "MajorityVote"}
        return _FakeArray()


class _FakePerfResult:
    def rx2(self, name):
        assert name == "choice.ncomp"
        return _FakeChoice()


class _FakeR:
    def __init__(self, perf_result):
        self.perf_result = perf_result
        self.perf_kwargs = None

    def __call__(self, expression):
        assert "library(mixOmics)" in expression

    def __getitem__(self, name):
        if name == "block.plsda":
            return lambda *args, **kwargs: object()
        if name == "perf":
            return self._perf
        if name == "rownames":
            return lambda value: ["Overall.BER", "Overall.ER"]
        if name == "colnames":
            return lambda value: ["max.dist"]
        raise KeyError(name)

    def _perf(self, *args, **kwargs):
        self.perf_kwargs = kwargs
        return self.perf_result


def test_tune_components_runs_perf_and_returns_error_rates(monkeypatch, capsys):
    action = importlib.import_module("q2_mfa.pls.tune_components_block_splsda")
    blocks = {"metabolome": pd.DataFrame([[1]]), "microbiome": pd.DataFrame([[2]])}
    target = pd.Series(["case"])
    expected = pd.DataFrame(
        {
            "vote": ["weighted"],
            "distance": ["max.dist"],
            "class": ["Overall.BER"],
            "component": [0],
            "statistic": ["mean"],
            "value": [0.2],
        }
    )
    fake_r = _FakeR(_FakePerfResult())

    monkeypatch.setattr(action, "r", fake_r)
    monkeypatch.setattr(action, "_align_samples", lambda tables, y: (blocks, target))
    monkeypatch.setattr(action, "_resolve_design", lambda *args: 0.1)
    monkeypatch.setattr(action, "_build_bpparam", lambda *args: "backend")
    monkeypatch.setattr(action, "_to_r_inputs", lambda *args: ("blocks", "y", "design"))
    monkeypatch.setattr(action.CaptureHolder, "get_or_set", lambda seed, factory: 42)
    monkeypatch.setattr(
        action,
        "_r_vote_error_rate_to_dataframe",
        lambda result, framework: expected.assign(
            vote="weighted" if framework == "WeightedVote" else "majority"
        ),
    )

    result = action.tune_components_block_splsda(
        tables=blocks,
        y=object(),
        design_weight=0.1,
        ncomp=4,
    )

    assert fake_r.perf_kwargs["nrepeat"] == 3
    assert fake_r.perf_kwargs["progressBar"] is False
    assert fake_r.perf_kwargs["BPPARAM"] == "backend"
    output = capsys.readouterr().out
    assert "WeightedVote component-choice matrix:" in output
    assert "Best ncomp chosen" not in output
    pd.testing.assert_frame_equal(
        result.error_rate,
        pd.concat([expected, expected.assign(vote="majority")], ignore_index=True),
    )
    assert result.ncomp_selection_choice_matrix.to_dict("records") == [
        {
            "vote": "weighted",
            "measure": "Overall.BER",
            "distance": "max.dist",
            "ncomp": 2,
        },
        {
            "vote": "weighted",
            "measure": "Overall.ER",
            "distance": "max.dist",
            "ncomp": 1,
        },
        {
            "vote": "majority",
            "measure": "Overall.BER",
            "distance": "max.dist",
            "ncomp": 2,
        },
        {
            "vote": "majority",
            "measure": "Overall.ER",
            "distance": "max.dist",
            "ncomp": 1,
        },
    ]


def test_tune_components_serializes_both_vote_frameworks(monkeypatch):
    action = importlib.import_module("q2_mfa.pls.tune_components_block_splsda")
    blocks = {"a": pd.DataFrame([[1]]), "b": pd.DataFrame([[2]])}
    target = pd.Series(["case"])
    captured = {}

    monkeypatch.setattr(action, "r", _FakeR(_FakePerfResult()))
    monkeypatch.setattr(action, "_align_samples", lambda tables, y: (blocks, target))
    monkeypatch.setattr(action, "_resolve_design", lambda *args: 0.1)
    monkeypatch.setattr(action, "_build_bpparam", lambda *args: "backend")
    monkeypatch.setattr(action, "_to_r_inputs", lambda *args: ("blocks", "y", "design"))
    monkeypatch.setattr(action.CaptureHolder, "get_or_set", lambda seed, factory: 42)

    def fake_error_rates(result, framework):
        captured.setdefault("frameworks", []).append(framework)
        return pd.DataFrame(
            columns=["vote", "distance", "class", "component", "statistic", "value"]
        )

    monkeypatch.setattr(action, "_r_vote_error_rate_to_dataframe", fake_error_rates)

    action.tune_components_block_splsda(tables=blocks, y=object(), design_weight=0.1)

    assert captured["frameworks"] == ["WeightedVote", "MajorityVote"]


def test_auto_threads_delegates_worker_count_to_biocparallel(monkeypatch):
    from q2_mfa.pls import utils

    calls = {}

    class FakeR:
        def __call__(self, expression):
            assert "library(BiocParallel)" in expression

        def __getitem__(self, name):
            def constructor(**kwargs):
                calls[name] = kwargs
                return name, kwargs

            return constructor

    monkeypatch.setattr(utils, "r", FakeR())
    monkeypatch.setattr(utils.platform, "system", lambda: "Darwin")

    backend, kwargs = utils._build_bpparam(0, 42)

    assert backend == "MulticoreParam"
    assert kwargs == {"RNGseed": 42}
    assert "workers" not in calls["MulticoreParam"]
