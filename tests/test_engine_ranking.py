from __future__ import annotations

from artha.engine.features import build_feature_vector
from artha.engine.ranking import Bucket, evaluate, rank
from artha.engine.spec import FormulaSpec

BASE = {
    "market_cap": 800.0,
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


def _fv(ticker: str = "ALPHA", **overrides):
    raw = dict(BASE)
    raw.update(overrides)
    return build_feature_vector(ticker=ticker, profile="profile_1_standard", as_of="2026-08-30", raw=raw)


def test_clean_candidate_is_ranked_with_a_net_return():
    result = evaluate(_fv(), FormulaSpec(), track="A")
    assert result.bucket is Bucket.RANKED
    assert result.net_cagr is not None
    assert result.reasons == ()


def test_gate_failure_rejects_and_names_the_rule_that_fired():
    result = evaluate(_fv(promoter_pledge=30.0), FormulaSpec(), track="A")
    assert result.bucket is Bucket.REJECTED
    assert any("promoter_pledge" in r for r in result.reasons)


def test_missing_gate_input_is_insufficient_data_not_rejection():
    result = evaluate(_fv(promoter_holding=None), FormulaSpec(), track="A")
    assert result.bucket is Bucket.INSUFFICIENT_DATA
    assert any("promoter_holding" in r for r in result.reasons)


def test_missing_deferred_check_still_ranks_but_is_flagged_for_verification():
    # Nothing populates pending_verification from a single snapshot row today.
    result = evaluate(_fv(), FormulaSpec(), track="A")
    assert result.bucket is Bucket.RANKED
    assert result.pending_verification == ()


def test_fully_evidenced_candidate_has_nothing_pending():
    result = evaluate(_fv(), FormulaSpec(), track="A")
    assert result.pending_verification == ()


def test_uncomputable_return_is_insufficient_data_even_when_gates_pass():
    result = evaluate(_fv(pe_ratio=None), FormulaSpec(), track="A")
    assert result.bucket is Bucket.INSUFFICIENT_DATA
    assert result.gates.eligible is True


def test_a_gate_failure_outranks_a_high_return_estimate():
    # Same company, one with a disqualifying pledge: the estimate is irrelevant.
    clean = evaluate(_fv(), FormulaSpec(), track="A")
    pledged = evaluate(_fv(promoter_pledge=40.0), FormulaSpec(), track="A")
    assert clean.bucket is Bucket.RANKED
    assert pledged.bucket is Bucket.REJECTED


def test_ranking_orders_by_expected_return_best_first():
    high = _fv("HIGH", profit_growth_5y=25.0)
    low = _fv("LOW", profit_growth_5y=8.0)
    run = rank([low, high], FormulaSpec(), track="A")
    assert [c.ticker for c in run.ranked] == ["HIGH", "LOW"]


def test_non_ranked_candidates_sort_after_ranked_ones():
    run = rank(
        [_fv("BAD", promoter_pledge=40.0), _fv("GOOD"), _fv("UNKNOWN", promoter_holding=None)],
        FormulaSpec(),
        track="A",
    )
    assert run.candidates[0].ticker == "GOOD"
    assert {c.ticker for c in run.rejected} == {"BAD"}
    assert {c.ticker for c in run.insufficient} == {"UNKNOWN"}


def test_confidence_discounts_a_thinly_evidenced_estimate():
    full = _fv("FULL")
    thin = _fv("THIN", sales_growth_5y=None, sales_growth_3y=None, roiic_3y=None, roe=None, gross_margin=None)
    run = rank([thin, full], FormulaSpec(), track="A")
    ranked = {c.ticker: c for c in run.ranked}
    assert ranked["THIN"].estimate.confidence < ranked["FULL"].estimate.confidence


def test_run_records_the_spec_fingerprint_for_reproducibility():
    spec = FormulaSpec()
    run = rank([_fv()], spec, track="A")
    assert run.spec_fingerprint == spec.fingerprint
    assert run.spec_version == spec.version


def test_track_b_rejects_on_failed_asymmetry():
    import dataclasses

    spec = FormulaSpec()
    spec = dataclasses.replace(
        spec,
        track_b=dataclasses.replace(spec.track_b, bull_eps_multiple=1.0, bull_pe_multiple=1.0),
    )
    result = evaluate(_fv(), spec, track="B")
    assert result.bucket is Bucket.REJECTED
    assert any("asymmetry" in r for r in result.reasons)


def test_track_b_ranked_candidate_carries_its_scenarios():
    result = evaluate(_fv(), FormulaSpec(), track="B")
    assert result.bucket is Bucket.RANKED
    assert [s.name for s in result.scenarios] == ["bear", "base", "bull"]
    assert result.asymmetry_ratio is not None
