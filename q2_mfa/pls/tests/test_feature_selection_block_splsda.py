import importlib

import pandas as pd
import pytest
from rpy2.robjects import r

from q2_mfa.pls.feature_selection_block_splsda import (
    _parse_keepx_collection,
    _resolve_ncomp,
    _selected_features_table,
    feature_selection_block_splsda,
)


def test_keepx_collection_requires_matching_named_blocks():
    assert _parse_keepx_collection({"a": "1,2", "b": "3"}, ["a", "b"]) == {
        "a": [1, 2],
        "b": [3],
    }
    with pytest.raises(ValueError, match="keys"):
        _parse_keepx_collection({"a": "1"}, ["a", "b"])


def test_keepx_collection_rejects_invalid_counts():
    with pytest.raises(ValueError, match="positive integers"):
        _parse_keepx_collection({"a": "0", "b": "2"}, ["a", "b"])


def test_auto_keepx_uses_given_collection_as_its_initial_grid(monkeypatch):
    tuning = importlib.import_module("q2_mfa.pls.feature_selection_block_splsda")

    blocks = {"a": pd.DataFrame([[1], [2]]), "b": pd.DataFrame([[3], [4]])}
    target = pd.Series(["x", "y"])
    captured = {}

    monkeypatch.setattr(tuning, "_align_samples", lambda tables, y: (blocks, target))
    monkeypatch.setattr(tuning, "_resolve_design", lambda *args: 0.1)
    monkeypatch.setattr(tuning.CaptureHolder, "get_or_set", lambda seed, factory: 42)
    monkeypatch.setattr(tuning, "_build_bpparam", lambda *args: object())
    monkeypatch.setattr(tuning, "r", lambda *args: None)

    class Result:
        keep_x = {"a": [1], "b": [2]}
        evaluation_cache = {1: {(1, 2): {"mean": 0.1, "sd": 0.01}}}

    def fake_auto(*args, **kwargs):
        captured.update(kwargs)
        return Result()

    monkeypatch.setattr(tuning, "adaptive_keepx_refinement", fake_auto)
    result = feature_selection_block_splsda(
        tables=blocks,
        y=target,
        design_weight=0.1,
        ncomp=1,
        keepx={"a": "1,3", "b": "2,4"},
        auto_keepx=True,
    )
    assert captured["initial_keepx"] == {"a": [1, 3], "b": [2, 4]}
    assert result.selected_features.to_dict("records") == [
        {"block": "a", "component": 0, "value": 1},
        {"block": "b", "component": 0, "value": 2},
    ]


def test_manual_keepx_requires_a_collection(monkeypatch):
    tuning = importlib.import_module("q2_mfa.pls.feature_selection_block_splsda")

    blocks = {"a": pd.DataFrame([[1]]), "b": pd.DataFrame([[2]])}
    target = pd.Series(["x"])
    monkeypatch.setattr(tuning, "_align_samples", lambda tables, y: (blocks, target))
    monkeypatch.setattr(tuning, "_resolve_design", lambda *args: 0.1)
    monkeypatch.setattr(tuning.CaptureHolder, "get_or_set", lambda seed, factory: 42)
    monkeypatch.setattr(tuning, "_build_bpparam", lambda *args: object())
    monkeypatch.setattr(tuning, "r", lambda *args: None)
    with pytest.raises(ValueError, match="required"):
        feature_selection_block_splsda(
            tables=blocks,
            y=target,
            design_weight=0.1,
            ncomp=1,
            keepx=None,
            auto_keepx=False,
        )


def test_resolve_ncomp_requires_an_artifact_when_ncomp_is_omitted():
    with pytest.raises(ValueError, match="ncomp or a tuned-components artifact"):
        _resolve_ncomp(None, None, True, "BER", "max.dist")


def test_resolve_ncomp_uses_matching_component_choice(monkeypatch):
    utils = importlib.import_module("q2_mfa.pls.utils")

    monkeypatch.setattr(
        utils,
        "table_jsonl_to_df",
        lambda _: pd.DataFrame(
            {
                "vote": ["weighted", "majority"],
                "measure": ["Overall.BER", "Overall.BER"],
                "distance": ["max.dist", "max.dist"],
                "ncomp": [2, 1],
            }
        ),
    )

    class ComponentTuning:
        class choice_matrix:
            @staticmethod
            def path_maker():
                return "choice.jsonl"

    assert _resolve_ncomp(None, ComponentTuning(), True, "BER", "max.dist") == 2
    assert _resolve_ncomp(None, ComponentTuning(), False, "BER", "max.dist") == 1


def test_manual_ncomp_and_tuned_components_are_mutually_exclusive():
    with pytest.raises(
        ValueError, match="ncomp or a tuned-components artifact, not both"
    ):
        _resolve_ncomp(3, object(), True, "BER", "max.dist")


def test_error_rate_conversion_preserves_r_component_number():
    from q2_mfa.pls.utils import _r_feature_selection_error_rate_statistic_to_dataframe

    rates = r(
        "matrix(c(0.1, 0.2), ncol = 1, " 'dimnames = list(c("5_5", "10_5"), "comp2"))'
    )
    result = _r_feature_selection_error_rate_statistic_to_dataframe(rates, "mean")
    assert result["component"].tolist() == [1, 1]


def test_feature_selection_error_rates_use_named_keepx_columns():
    import pandas as pd

    from q2_mfa.pls.utils import _expand_keepx_columns

    result = _expand_keepx_columns(
        pd.DataFrame(
            {
                "keepx": ["1_2", "1_2"],
                "component": [0, 0],
                "statistic": ["mean", "sd"],
                "value": [0.12, 0.03],
            }
        ),
        ("metabolome", "microbiome"),
    )
    assert result.to_dict("records") == [
        {
            "component": 0,
            "statistic": "mean",
            "value": 0.12,
            "keepx_metabolome": 1,
            "keepx_microbiome": 2,
        },
        {
            "component": 0,
            "statistic": "sd",
            "value": 0.03,
            "keepx_metabolome": 1,
            "keepx_microbiome": 2,
        },
    ]


def test_selected_features_use_zero_based_component_labels():
    result = _selected_features_table({"metabolome": [5, 7], "microbiome": [3, 4]})
    assert result.to_dict("records") == [
        {"block": "metabolome", "component": 0, "value": 5},
        {"block": "metabolome", "component": 1, "value": 7},
        {"block": "microbiome", "component": 0, "value": 3},
        {"block": "microbiome", "component": 1, "value": 4},
    ]
