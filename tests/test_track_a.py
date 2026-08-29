from __future__ import annotations

from artha.screening.models import CompanyRecord, Outcome
from artha.screening.track_a import (
    clears_track_a_stage1,
    graham_defensive_criteria,
    growth_gate,
    moat_quality_refinement,
    quality_gate,
    run_track_a_stage1,
)

PASSING_QUALITY_FIELDS = {
    "roe": 18,
    "roce": 20,
    "debt_to_equity": 0.5,
    "ocf_to_pat": 0.9,
    "promoter_holding_pct": 55,
    "promoter_holding_trend_3y": 1.0,
}


def _record(fields: dict, profile: str = "profile_1_standard") -> CompanyRecord:
    return CompanyRecord(ticker="ALPHA", arithmetic_profile=profile, fields=fields)


def test_quality_gate_passes_when_all_thresholds_met():
    result = quality_gate(_record(PASSING_QUALITY_FIELDS))
    assert result.outcome == Outcome.PASS


def test_quality_gate_fails_on_low_roe():
    fields = dict(PASSING_QUALITY_FIELDS, roe=10)
    result = quality_gate(_record(fields))
    assert result.outcome == Outcome.FAIL


def test_quality_gate_fails_on_declining_promoter_holding_even_if_above_50():
    fields = dict(PASSING_QUALITY_FIELDS, promoter_holding_trend_3y=-2.0)
    result = quality_gate(_record(fields))
    assert result.outcome == Outcome.FAIL


def test_quality_gate_needs_stage_1b_when_roe_missing():
    fields = dict(PASSING_QUALITY_FIELDS)
    del fields["roe"]
    result = quality_gate(_record(fields))
    assert result.outcome == Outcome.NEEDS_STAGE_1B
    assert "roe" in result.missing_data_fields


def test_quality_gate_not_applicable_for_non_standard_profile():
    result = quality_gate(_record(PASSING_QUALITY_FIELDS, profile="profile_2_banking"))
    assert result.outcome == Outcome.NOT_APPLICABLE


def test_growth_gate_passes_on_pat_cagr_and_flags_eps_decline_as_stage_1b():
    result = growth_gate(_record({"profit_growth_5y": 18}))
    # The mandatory PAT CAGR criterion passes, so growth_gate itself passes,
    # even though "no year of EPS decline" is unresolved (non-mandatory here).
    assert result.outcome == Outcome.PASS
    eps_criterion = next(c for c in result.criteria if c.name == "no_year_of_eps_decline")
    assert eps_criterion.outcome == Outcome.NEEDS_STAGE_1B


def test_growth_gate_fails_on_low_pat_cagr():
    result = growth_gate(_record({"profit_growth_5y": 5}))
    assert result.outcome == Outcome.FAIL


def test_moat_quality_refinement_is_non_gating_but_reports_all_criteria():
    result = moat_quality_refinement(_record({"gross_margin": 55, "roce": 25, "interest_coverage": 12, "fcf_conversion_pct": 85}))
    # ROE/ROIC 10yr sustained test always needs Stage 1b, so the composite
    # outcome reflects that even when every single-point ratio passes.
    assert result.outcome == Outcome.NEEDS_STAGE_1B
    threshold_criteria = [c for c in result.criteria if c.name != "roe_roic_sustained_10y"]
    assert all(c.outcome == Outcome.PASS for c in threshold_criteria)


def test_graham_defensive_criteria_computes_graham_number():
    result = graham_defensive_criteria(_record({"current_ratio": 2.5, "pe_ratio": 12, "price_to_book": 1.2}))
    gn_criterion = next(c for c in result.criteria if c.name == "graham_number_at_most_22_5")
    assert gn_criterion.outcome == Outcome.PASS
    assert "14.4" in gn_criterion.detail  # 12 * 1.2


def test_graham_defensive_criteria_fails_graham_number_when_too_high():
    result = graham_defensive_criteria(_record({"current_ratio": 2.5, "pe_ratio": 20, "price_to_book": 2.0}))
    gn_criterion = next(c for c in result.criteria if c.name == "graham_number_at_most_22_5")
    assert gn_criterion.outcome == Outcome.FAIL


def test_clears_track_a_stage1_requires_both_mandatory_gates():
    results = run_track_a_stage1(_record(PASSING_QUALITY_FIELDS | {"profit_growth_5y": 18}))
    assert clears_track_a_stage1(results) is True

    failing_fields = dict(PASSING_QUALITY_FIELDS, roe=5) | {"profit_growth_5y": 18}
    failing_results = run_track_a_stage1(_record(failing_fields))
    assert clears_track_a_stage1(failing_results) is False
