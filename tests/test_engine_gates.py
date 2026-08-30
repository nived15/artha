from __future__ import annotations

from artha.engine.features import build_feature_vector
from artha.engine.gates import GateStatus, run_hard_gates
from artha.engine.spec import FormulaSpec

PASSING = {
    "market_cap": 800.0,
    "promoter_pledge": 0.0,
    "promoter_holding": 55.0,
    "debt_to_equity": 0.4,
}


def _fv(profile: str = "profile_1_standard", **overrides):
    raw = dict(PASSING)
    raw.update(overrides)
    return build_feature_vector(ticker="ALPHA", profile=profile, as_of="2026-08-30", raw=raw)


def _status(report, name: str) -> GateStatus:
    return next(r.status for r in report.results if r.name == name)


def test_clean_company_clears_every_hard_gate():
    report = run_hard_gates(_fv(), FormulaSpec())
    assert report.eligible is True
    assert report.failures == ()
    assert report.unknowns == ()


def test_excess_pledge_is_a_definitive_failure():
    report = run_hard_gates(_fv(promoter_pledge=30.0), FormulaSpec())
    assert report.eligible is False
    assert _status(report, "promoter_pledge") is GateStatus.FAIL
    assert [r.name for r in report.failures] == ["promoter_pledge"]
    assert report.unknowns == ()


def test_missing_input_blocks_but_is_reported_as_unknown_not_failure():
    report = run_hard_gates(_fv(promoter_holding=None), FormulaSpec())
    assert report.eligible is False
    assert _status(report, "promoter_holding") is GateStatus.INSUFFICIENT_DATA
    assert report.failures == ()
    assert [r.name for r in report.unknowns] == ["promoter_holding"]
    assert report.missing_features == ("promoter_holding",)


def test_failure_and_unknown_are_reported_separately_in_the_same_run():
    report = run_hard_gates(_fv(promoter_pledge=30.0, promoter_holding=None), FormulaSpec())
    assert [r.name for r in report.failures] == ["promoter_pledge"]
    assert [r.name for r in report.unknowns] == ["promoter_holding"]


def test_accounting_quality_is_not_a_gate():
    # OCF/PAT is not exportable from Screener, so cash conversion cannot be a
    # Stage 1a gate at all; it moves to Stage 3 filing review.
    report = run_hard_gates(_fv(), FormulaSpec())
    assert "accounting_quality" not in [r.name for r in report.results]


def test_leverage_gate_is_dropped_for_lending_profiles_not_failed():
    report = run_hard_gates(_fv(profile="profile_2_banking", debt_to_equity=8.0), FormulaSpec())
    assert _status(report, "solvency") is GateStatus.NOT_APPLICABLE
    assert report.eligible is True


def test_leverage_gate_still_bites_for_standard_profiles():
    report = run_hard_gates(_fv(debt_to_equity=8.0), FormulaSpec())
    assert _status(report, "solvency") is GateStatus.FAIL


def test_below_liquidity_floor_fails():
    report = run_hard_gates(_fv(market_cap=50.0), FormulaSpec())
    assert _status(report, "liquidity") is GateStatus.FAIL


def test_gate_result_records_the_features_it_used():
    report = run_hard_gates(_fv(), FormulaSpec())
    pledge = next(r for r in report.results if r.name == "promoter_pledge")
    assert pledge.features_used == ("promoter_pledge",)
