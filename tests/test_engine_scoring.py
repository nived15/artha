from __future__ import annotations

import pytest

from artha.engine.features import build_feature_vector
from artha.engine.scoring import quality_score, ramp, score_all, value_score


def _fv(**raw):
    return build_feature_vector(ticker="ALPHA", profile="profile_1_standard", as_of="2026-08-30", raw=raw)


def test_ramp_clips_at_both_ends():
    assert ramp(0.05, 0.10, 0.30) == 0.0
    assert ramp(0.40, 0.10, 0.30) == 1.0
    assert ramp(0.20, 0.10, 0.30) == pytest.approx(0.5)


def test_ramp_supports_descending_scales_for_cheapness():
    # Lower P/E should score higher.
    assert ramp(8.0, 40.0, 8.0) == 1.0
    assert ramp(40.0, 40.0, 8.0) == 0.0
    assert ramp(24.0, 40.0, 8.0) == pytest.approx(0.5)


def test_ramp_returns_none_for_missing_input():
    assert ramp(None, 0.0, 1.0) is None


def test_full_inputs_give_full_confidence():
    score = quality_score(_fv(roce=30.0, roe=28.0, interest_coverage=12.0, gross_margin=60.0))
    assert score.confidence == pytest.approx(1.0)
    assert score.value == pytest.approx(1.0)
    assert score.missing == ()


def test_partial_inputs_reduce_confidence_but_still_score():
    score = quality_score(_fv(roce=30.0, roe=28.0))
    # roce 0.35 + roe 0.30 of the total weight is available.
    assert score.confidence == pytest.approx(0.65)
    assert score.value == pytest.approx(1.0)
    assert set(score.missing) == {"interest_coverage", "gross_margin"}


def test_no_inputs_gives_zero_confidence_and_no_credit():
    score = quality_score(_fv())
    assert score.confidence == 0.0
    assert score.value == 0.0


def test_scorecard_confidence_is_the_mean_across_composites():
    card = score_all(_fv(roce=30.0, roe=28.0, interest_coverage=12.0, gross_margin=60.0))
    assert card.quality.confidence == pytest.approx(1.0)
    # Growth, value and governance have no inputs at all here.
    assert card.confidence == pytest.approx(0.25)


def test_missing_features_are_aggregated_across_the_scorecard():
    card = score_all(_fv(roce=30.0))
    assert "profit_growth_5y" in card.missing_features
    assert "promoter_holding" in card.missing_features


# --- lender valuation substitution (plan.md 5.4) -----------------------------


def _lender(**raw):
    return build_feature_vector(
        ticker="BANK", profile="profile_2_banking", as_of="2026-08-30", raw=raw
    )


def test_standard_profile_uses_ebit_over_enterprise_value():
    score = value_score(_fv(ebit=100.0, enterprise_value=1000.0))
    ey = next(c for c in score.components if c.name == "earnings_yield")
    assert "EBIT/EV" in ey.detail
    assert ey.value == pytest.approx(ramp(0.10, 0.04, 0.18))


def test_lender_substitutes_pat_over_market_cap_and_flags_it():
    # A bank's EV sweeps in deposits, so EBIT/EV is meaningless; 1/(P/E) is
    # the plan's substitute and must be used even when EBIT and EV exist.
    score = value_score(_lender(pe_ratio=10.0, ebit=100.0, enterprise_value=999999.0))
    ey = next(c for c in score.components if c.name == "earnings_yield")
    assert "PAT/MarketCap" in ey.detail
    assert "Artha substitution" in ey.detail
    assert ey.value == pytest.approx(ramp(0.10, 0.04, 0.18))


def test_lender_drops_the_redundant_pe_leg():
    names = {c.name for c in value_score(_lender(pe_ratio=10.0)).components}
    assert names == {"earnings_yield", "price_to_book"}


def test_lender_without_a_usable_pe_has_no_earnings_yield():
    score = value_score(_lender(pe_ratio=0.0, price_to_book=2.0))
    ey = next(c for c in score.components if c.name == "earnings_yield")
    assert ey.value is None
    assert score.confidence == pytest.approx(0.45)
