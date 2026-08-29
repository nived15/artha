from __future__ import annotations

import pytest

from artha.screening.models import CompanyRecord, Outcome
from artha.screening.track_b import (
    canslim_overlay,
    clears_track_b_stage1,
    davis_double_play,
    davis_double_play_implied_return,
    kedia_smile,
    lynch_peg,
    run_track_b_stage1,
)


def _record(fields: dict) -> CompanyRecord:
    return CompanyRecord(ticker="BETA", arithmetic_profile="profile_1_standard", fields=fields)


def test_lynch_peg_fast_grower_in_buy_zone():
    # PE=15, growth=25% (fast grower, no dividend adjustment) -> PEG = 15/25 = 0.6
    result = lynch_peg(_record({"pe_ratio": 15, "profit_growth_5y": 25}))
    assert result.outcome == Outcome.PASS
    assert result.score == pytest.approx(0.6)


def test_lynch_peg_stalwart_uses_dividend_adjustment():
    # stalwart (growth=10%), dividend yield=2% -> denominator=12, PEG = 12/12 = 1.0 (not < 1.0 -> fail)
    result = lynch_peg(_record({"pe_ratio": 12, "profit_growth_5y": 10, "dividend_yield_pct": 2}))
    assert result.score == pytest.approx(1.0)
    assert result.outcome == Outcome.FAIL


def test_lynch_peg_needs_stage_1b_when_growth_missing():
    result = lynch_peg(_record({"pe_ratio": 15}))
    assert result.outcome == Outcome.NEEDS_STAGE_1B


def test_davis_double_play_implied_return_formula():
    # (1.15)^3 * (20/10) - 1
    value = davis_double_play_implied_return(entry_pe=10, sector_median_pe=20, trailing_eps_cagr_pct=15)
    expected = (1.15**3) * 2.0 - 1
    assert value == pytest.approx(expected)


def test_davis_double_play_implied_return_rejects_non_positive_entry_pe():
    with pytest.raises(ValueError):
        davis_double_play_implied_return(entry_pe=0, sector_median_pe=20, trailing_eps_cagr_pct=15)


def test_davis_double_play_needs_stage_1b_without_percentile_and_sector_median():
    result = davis_double_play(_record({"pe_ratio": 10, "profit_growth_5y": 20, "roe": 18, "debt_to_equity": 1.0}))
    assert result.outcome == Outcome.NEEDS_STAGE_1B
    percentile_criterion = next(c for c in result.criteria if c.name == "entry_pe_bottom_tercile_5y")
    assert percentile_criterion.outcome == Outcome.NEEDS_STAGE_1B


def test_davis_double_play_passes_when_all_supplied_and_favorable():
    result = davis_double_play(
        _record(
            {
                "pe_ratio": 10,
                "profit_growth_5y": 20,
                "roe": 18,
                "debt_to_equity": 1.0,
                "eps_growth_latest_q_yoy": 5,
                "eps_growth_ttm_yoy": 3,
            }
        ),
        entry_pe_percentile_5y=20.0,
        sector_median_pe=15.0,
    )
    assert result.outcome == Outcome.PASS


def test_davis_double_play_fails_pe_floor():
    result = davis_double_play(
        _record({"pe_ratio": 3, "profit_growth_5y": 20, "roe": 18, "debt_to_equity": 1.0}),
        entry_pe_percentile_5y=20.0,
        sector_median_pe=15.0,
    )
    assert result.outcome == Outcome.FAIL


def test_kedia_smile_passes_within_band():
    result = kedia_smile(
        _record(
            {
                "market_cap": 1000,
                "years_since_incorporation": 20,
                "promoter_holding_pct": 50,
                "analyst_coverage_count": 1,
            }
        )
    )
    assert result.outcome == Outcome.PASS
    # The qualitative L/E letters are informational, not gating.
    le_criterion = next(c for c in result.criteria if c.name == "large_aspiration_and_tam")
    assert le_criterion.outcome == Outcome.NEEDS_STAGE_3


def test_kedia_smile_fails_outside_market_cap_band():
    result = kedia_smile(
        _record(
            {
                "market_cap": 8000,  # above the 5000 Cr ceiling
                "years_since_incorporation": 20,
                "promoter_holding_pct": 50,
                "analyst_coverage_count": 1,
            }
        )
    )
    assert result.outcome == Outcome.FAIL


def test_canslim_overlay_needs_stage_3_without_technical_feed():
    result = canslim_overlay(_record({"eps_growth_latest_q_yoy": 30, "profit_growth_3y": 30, "roe": 20}))
    assert result.outcome == Outcome.NEEDS_STAGE_3


def test_canslim_overlay_passes_when_all_inputs_supplied():
    result = canslim_overlay(
        _record({"eps_growth_latest_q_yoy": 30, "profit_growth_3y": 30, "roe": 20}),
        price_within_5pct_of_pivot=True,
        breakout_volume_ratio=1.5,
        relative_strength_percentile=90,
        market_in_uptrend=True,
    )
    assert result.outcome == Outcome.PASS


def test_clears_track_b_stage1_is_any_of_three_screens():
    # Only Kedia SMILE passes; Lynch/Davis need Stage 1b data.
    results = run_track_b_stage1(
        _record(
            {
                "market_cap": 1000,
                "years_since_incorporation": 20,
                "promoter_holding_pct": 50,
                "analyst_coverage_count": 1,
            }
        )
    )
    assert clears_track_b_stage1(results) is True
