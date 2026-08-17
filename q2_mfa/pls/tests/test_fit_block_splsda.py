import pandas as pd
import pytest

from q2_mfa.pls.utils import (
    _component_keepx_from_feature_selection,
    _feature_component_correlation_to_dataframe,
    _parse_fit_keepx,
    _r_feature_similarity_to_dataframe,
    _r_vote_error_rate_to_dataframe,
    _resolve_fit_keepx,
)


def test_manual_keepx_strings_follow_component_then_block_order():
    assert _parse_fit_keepx(
        {"first": "5,3", "second": "7,4"},
        ["metabolome", "microbiome"],
        2,
    ) == {"metabolome": [5, 7], "microbiome": [3, 4]}


def test_manual_keepx_requires_one_string_per_component():
    with pytest.raises(ValueError, match="expected 2, received 1"):
        _parse_fit_keepx({"first": "5,3"}, ["metabolome", "microbiome"], 2)


def test_feature_selection_artifact_values_become_component_strings(monkeypatch):
    import q2_mfa.pls.utils as utils

    monkeypatch.setattr(
        utils,
        "table_jsonl_to_df",
        lambda _: pd.DataFrame(
            [
                {"block": "metabolome", "component": 0, "value": 5},
                {"block": "microbiome", "component": 0, "value": 3},
                {"block": "metabolome", "component": 1, "value": 7},
                {"block": "microbiome", "component": 1, "value": 4},
            ]
        ),
    )

    class FeatureSelection:
        class selected_features:
            @staticmethod
            def path_maker():
                return "selected-features.jsonl"

    assert _component_keepx_from_feature_selection(
        FeatureSelection(), ["metabolome", "microbiome"], 2
    ) == {"component-1": "5,3", "component-2": "7,4"}


def test_keepx_sources_are_mutually_exclusive():
    with pytest.raises(ValueError, match="keepx or a feature-selection artifact"):
        _resolve_fit_keepx({"first": "5,3"}, object(), ["metabolome", "microbiome"], 1)


def test_feature_component_correlations_include_selected_features_and_components():
    blocks = {
        "metabolome": pd.DataFrame({"m1": [1, 2, 3], "m2": [3, 2, 1]}),
        "microbiome": pd.DataFrame({"t1": [3, 2, 1]}),
    }
    variates = {
        "metabolome": pd.DataFrame({"comp1": [1, 2, 3], "comp2": [3, 2, 1]}),
        "microbiome": pd.DataFrame({"comp1": [1, 2, 3], "comp2": [3, 2, 1]}),
    }
    loadings = {
        "metabolome": pd.DataFrame(
            {"comp1": [1, 0], "comp2": [0, 2]}, index=["m1", "m2"]
        ),
        "microbiome": pd.DataFrame({"comp1": [1], "comp2": [1]}, index=["t1"]),
    }

    observed = _feature_component_correlation_to_dataframe(blocks, variates, loadings)

    assert observed.to_dict("records") == [
        {"block": "metabolome", "feature": "m1", "component": 0, "value": 1.0},
        {"block": "metabolome", "feature": "m2", "component": 1, "value": 1.0},
        {"block": "microbiome", "feature": "t1", "component": 0, "value": -1.0},
        {"block": "microbiome", "feature": "t1", "component": 1, "value": 1.0},
    ]


def test_circos_similarity_is_serialized_as_unique_feature_pairs(monkeypatch):
    import q2_mfa.pls.utils as utils

    class FakeR:
        def __getitem__(self, name):
            assert name == "circosPlot"
            return lambda *args, **kwargs: [
                [1.0, 0.2, 0.3],
                [0.2, 1.0, 0.4],
                [0.3, 0.4, 1.0],
            ]

    monkeypatch.setattr(utils, "r", FakeR())
    blocks = {
        "first": pd.DataFrame({"a": [1], "b": [2]}),
        "second": pd.DataFrame({"c": [3]}),
    }
    loadings = {
        "first": pd.DataFrame({"comp1": [1, 1]}, index=["a", "b"]),
        "second": pd.DataFrame({"comp1": [1]}, index=["c"]),
    }

    observed = _r_feature_similarity_to_dataframe(object(), blocks, loadings, 1)

    assert observed.to_dict("records") == [
        {
            "block_1": "first",
            "feature_1": "a",
            "block_2": "first",
            "feature_2": "b",
            "value": 0.2,
        },
        {
            "block_1": "first",
            "feature_1": "a",
            "block_2": "second",
            "feature_2": "c",
            "value": 0.3,
        },
        {
            "block_1": "first",
            "feature_1": "b",
            "block_2": "second",
            "feature_2": "c",
            "value": 0.4,
        },
    ]


def test_vote_error_rates_include_weighted_and_majority_labels(monkeypatch):
    import q2_mfa.pls.utils as utils

    monkeypatch.setattr(
        utils,
        "_r_vote_error_rate_statistic_to_dataframe",
        lambda _rates, statistic, vote: pd.DataFrame(
            [
                {
                    "vote": vote.removesuffix("Vote").lower(),
                    "distance": "max.dist",
                    "class": "Overall.BER",
                    "component": 0,
                    "statistic": statistic,
                    "value": 0.2,
                }
            ]
        ),
    )

    class Perf:
        def rx2(self, name):
            return name

    observed = pd.concat(
        [
            _r_vote_error_rate_to_dataframe(Perf(), "WeightedVote"),
            _r_vote_error_rate_to_dataframe(Perf(), "MajorityVote"),
        ],
        ignore_index=True,
    )
    assert set(observed["vote"]) == {"weighted", "majority"}
    assert list(observed.columns) == [
        "vote",
        "distance",
        "class",
        "component",
        "statistic",
        "value",
    ]
