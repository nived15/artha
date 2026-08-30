from __future__ import annotations

from artha.engine.features import FEATURES, Unit, build_feature_vector, normalise


def test_percent_features_are_stored_as_decimals():
    fv = build_feature_vector(
        ticker="ALPHA",
        profile="profile_1_standard",
        as_of="2026-08-30",
        raw={"roe": 18.0, "roce": 22.0, "promoter_pledge": 25.0},
    )
    assert fv.get("roe") == 0.18
    assert fv.get("roce") == 0.22
    assert fv.get("promoter_pledge") == 0.25


def test_ratio_features_pass_through_unscaled():
    fv = build_feature_vector(
        ticker="ALPHA",
        profile="profile_1_standard",
        as_of="2026-08-30",
        raw={"debt_to_equity": 0.4, "current_ratio": 2.5},
    )
    assert fv.get("debt_to_equity") == 0.4
    assert fv.get("current_ratio") == 2.5


def test_unknown_feature_names_are_dropped_not_carried():
    fv = build_feature_vector(
        ticker="ALPHA",
        profile="profile_1_standard",
        as_of="2026-08-30",
        raw={"roe": 18.0, "not_a_real_feature": 5.0},
    )
    assert "not_a_real_feature" not in fv.values
    assert fv.get("not_a_real_feature") is None


def test_none_values_are_omitted_so_missing_stays_missing():
    fv = build_feature_vector(
        ticker="ALPHA",
        profile="profile_1_standard",
        as_of="2026-08-30",
        raw={"roe": None, "roce": 20.0},
    )
    assert fv.get("roe") is None
    assert fv.missing("roe", "roce") == ("roe",)
    assert fv.has("roce") is True
    assert fv.has("roe", "roce") is False


def test_text_features_are_not_coerced_to_float():
    fv = build_feature_vector(
        ticker="ALPHA",
        profile="profile_1_standard",
        as_of="2026-08-30",
        raw={"sector": "Industrial Minerals"},
    )
    assert fv.text("sector") == "Industrial Minerals"
    assert fv.get("sector") is None


def test_non_numeric_value_for_numeric_feature_becomes_missing():
    assert normalise("roe", "not a number") is None


def test_every_declared_feature_has_a_unit():
    assert all(isinstance(spec.unit, Unit) for spec in FEATURES.values())
