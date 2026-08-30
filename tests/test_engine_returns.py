from __future__ import annotations

import dataclasses

import pytest

from artha.engine.features import build_feature_vector
from artha.engine.returns import (
    after_tax_cagr,
    default_probability_model,
    estimate_track_a,
    estimate_track_b,
    fair_pe,
    rerating_cagr,
)
from artha.engine.scoring import score_all
from artha.engine.spec import FormulaSpec

# A deliberately complete company, so every component is exercised.
COMPLETE = {
    "pe_ratio": 20.0,
    "dividend_yield": 1.0,
    "profit_growth_5y": 18.0,
    "sales_growth_5y": 15.0,
    "profit_growth_3y": 20.0,
    "roiic_3y": 30.0,
    "reinvestment_rate": 0.5,
    "roce": 30.0,
    "roe": 28.0,
    "interest_coverage": 12.0,
    "gross_margin": 60.0,
    "promoter_holding": 55.0,
    "promoter_holding_trend_3y": 1.0,
    "promoter_pledge": 0.0,
    "debt_to_equity": 0.4,
    "current_ratio": 2.5,
}


def _fv(**overrides):
    raw = dict(COMPLETE)
    raw.update(overrides)
    return build_feature_vector(ticker="ALPHA", profile="profile_1_standard", as_of="2026-08-30", raw=raw)


# --- tax arithmetic ---------------------------------------------------------


def test_after_tax_cagr_reconciles_by_hand():
    # 1.2^5 = 2.48832; gain 1.48832 taxed at 12.5% leaves 1.30228;
    # terminal 2.30228; 2.30228^(1/5) - 1 = 0.18149
    assert after_tax_cagr(0.20, 5.0, 0.125) == pytest.approx(0.18149, abs=1e-5)


def test_losses_receive_no_tax_credit():
    assert after_tax_cagr(-0.10, 5.0, 0.125) == -0.10


def test_zero_growth_is_untaxed():
    assert after_tax_cagr(0.0, 5.0, 0.125) == 0.0


# --- valuation term ---------------------------------------------------------


def test_fair_pe_rises_with_growth_and_quality():
    spec = FormulaSpec()
    assert fair_pe(0.05, 0.5, spec) < fair_pe(0.20, 0.5, spec)
    assert fair_pe(0.10, 0.2, spec) < fair_pe(0.10, 0.9, spec)


def test_fair_pe_is_clamped_to_the_configured_band():
    spec = FormulaSpec()
    assert fair_pe(1.0, 1.0, spec) == spec.valuation.max_fair_pe
    assert fair_pe(-1.0, 0.0, spec) == spec.valuation.min_fair_pe


def test_rerating_is_capped_in_both_directions():
    spec = FormulaSpec()
    cap = spec.valuation.max_annual_rerating
    assert rerating_cagr(10.0, 45.0, 5.0, spec) == pytest.approx(cap)
    assert rerating_cagr(45.0, 10.0, 5.0, spec) == pytest.approx(-cap)


# --- Track A ----------------------------------------------------------------


def test_track_a_growth_blend_reconciles_by_hand():
    spec = FormulaSpec()
    est = estimate_track_a(_fv(), score_all(_fv()), spec)
    # raw blend 0.5*0.18 + 0.3*0.15 + 0.2*(0.30*0.5) = 0.165, then soft-capped:
    # 0.30*(1 - e^(-0.165/0.30)) = 0.126915
    assert est.components["growth"] == pytest.approx(0.126915, abs=1e-6)


def test_track_a_full_estimate_reconciles_by_hand():
    spec = FormulaSpec()
    fv = _fv()
    est = estimate_track_a(fv, score_all(fv), spec)
    assert est.computable is True
    # growth 0.126915 + carry 0.01 + capped rerating 0.06 - risk 0.003667
    assert est.components["rerating"] == pytest.approx(spec.valuation.max_annual_rerating)
    assert est.gross_cagr == pytest.approx(0.193248, abs=1e-5)
    assert est.net_cagr == pytest.approx(0.175212, abs=1e-5)


def test_tax_always_reduces_a_positive_return():
    fv = _fv()
    est = estimate_track_a(fv, score_all(fv), FormulaSpec())
    assert est.net_cagr < est.gross_cagr
    assert est.tau_tax > 0


def test_growth_approaches_the_cap_without_ever_reaching_it():
    spec = FormulaSpec()
    fv = _fv(profit_growth_5y=90.0, sales_growth_5y=90.0, roiic_3y=90.0, reinvestment_rate=1.0)
    est = estimate_track_a(fv, score_all(fv), spec)
    assert est.components["growth"] == pytest.approx(0.285064, abs=1e-6)
    assert est.components["growth"] < spec.growth.cap


def test_soft_cap_preserves_ordering_above_the_cap():
    # The whole point: a hard clip would tie these two at 0.30.
    spec = FormulaSpec()
    faster = _fv(profit_growth_5y=120.0, sales_growth_5y=120.0)
    slower = _fv(profit_growth_5y=60.0, sales_growth_5y=60.0)
    a = estimate_track_a(faster, score_all(faster), spec).components["growth"]
    b = estimate_track_a(slower, score_all(slower), spec).components["growth"]
    assert a > b
    assert a < spec.growth.cap


def test_track_a_is_not_computable_without_an_entry_pe():
    fv = _fv(pe_ratio=None)
    est = estimate_track_a(fv, score_all(fv), FormulaSpec())
    assert est.computable is False
    assert est.net_cagr is None
    assert any("entry P/E" in b for b in est.blockers)


def test_track_a_is_not_computable_without_any_growth_input():
    fv = _fv(
        profit_growth_5y=None,
        profit_growth_3y=None,
        sales_growth_5y=None,
        sales_growth_3y=None,
        roiic_3y=None,
    )
    est = estimate_track_a(fv, score_all(fv), FormulaSpec())
    assert est.computable is False
    assert any("growth input" in b for b in est.blockers)


def test_informational_notes_are_kept_out_of_blockers():
    fv = _fv(profit_growth_5y=None, sales_growth_5y=None, sales_growth_3y=15.0)
    est = estimate_track_a(fv, score_all(fv), FormulaSpec())
    assert est.computable is True
    assert est.blockers == ()
    assert any("3y series" in n for n in est.notes)


def test_earnings_leg_falls_back_to_the_3y_series_and_says_so():
    fv = _fv(profit_growth_5y=None, sales_growth_5y=None, sales_growth_3y=15.0)
    est = estimate_track_a(fv, score_all(fv), FormulaSpec())
    assert est.computable is True
    # raw 0.5*0.20 + 0.3*0.15 + 0.2*(0.30*0.5) = 0.175, soft-capped to 0.132589
    assert est.components["growth"] == pytest.approx(0.132589, abs=1e-6)
    assert any("3y series" in n for n in est.notes)


def test_a_leg_with_no_3y_fallback_is_dropped_and_weights_renormalise():
    # COMPLETE carries no sales_growth_3y, so removing the 5y series drops the
    # sales leg entirely: raw (0.5*0.18 + 0.2*0.15) / 0.7 = 0.171429 -> 0.130585
    fv = _fv(sales_growth_5y=None)
    est = estimate_track_a(fv, score_all(fv), FormulaSpec())
    assert est.components["growth"] == pytest.approx(0.130585, abs=1e-6)


def test_partial_growth_inputs_lower_confidence():
    full = _fv()
    partial = _fv(sales_growth_5y=None, sales_growth_3y=None, roiic_3y=None)
    full_est = estimate_track_a(full, score_all(full), FormulaSpec())
    partial_est = estimate_track_a(partial, score_all(partial), FormulaSpec())
    assert partial_est.confidence < full_est.confidence


# --- Track B ----------------------------------------------------------------


def test_probability_model_is_a_valid_distribution_and_monotone():
    for setup in (0.0, 0.25, 0.5, 0.75, 1.0):
        bear, base, bull = default_probability_model(setup)
        assert bear >= 0 and base >= 0 and bull >= 0
        assert bear + base + bull == pytest.approx(1.0)
    assert default_probability_model(1.0)[2] > default_probability_model(0.0)[2]


def test_track_b_scenarios_reconcile_by_hand():
    fv = _fv()
    result = estimate_track_b(fv, score_all(fv), FormulaSpec())
    by_name = {s.name: s.total_return for s in result.scenarios}
    assert by_name["bear"] == pytest.approx(0.75 * 0.70 - 1.0)
    assert by_name["base"] == pytest.approx(1.35 * 1.00 - 1.0)
    assert by_name["bull"] == pytest.approx(2.10 * 1.40 - 1.0)


def test_track_b_asymmetry_ratio_reconciles_by_hand():
    fv = _fv()
    result = estimate_track_b(fv, score_all(fv), FormulaSpec())
    # 1.94 / 0.475
    assert result.asymmetry_ratio == pytest.approx(4.0842, abs=1e-4)
    assert result.asymmetry_passed is True


def test_track_b_fails_asymmetry_when_the_bull_case_is_thin():
    spec = FormulaSpec()
    spec = dataclasses.replace(
        spec,
        track_b=dataclasses.replace(spec.track_b, bull_eps_multiple=1.0, bull_pe_multiple=1.0),
    )
    fv = _fv()
    result = estimate_track_b(fv, score_all(fv), spec)
    assert result.asymmetry_passed is False


def test_track_b_probabilities_are_recorded_on_the_estimate():
    fv = _fv()
    result = estimate_track_b(fv, score_all(fv), FormulaSpec())
    c = result.estimate.components
    assert c["p_bear"] + c["p_base"] + c["p_bull"] == pytest.approx(1.0)


def test_track_b_accepts_an_injected_probability_model():
    fv = _fv()
    always_bull = lambda _s: (0.0, 0.0, 1.0)  # noqa: E731
    result = estimate_track_b(fv, score_all(fv), FormulaSpec(), always_bull)
    assert result.estimate.components["expected_total_return"] == pytest.approx(1.94)


def test_track_b_is_not_computable_without_an_entry_pe():
    fv = _fv(pe_ratio=None)
    result = estimate_track_b(fv, score_all(fv), FormulaSpec())
    assert result.estimate.computable is False
    assert result.scenarios == ()
