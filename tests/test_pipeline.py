from __future__ import annotations

from artha.screening.models import CompanyRecord
from artha.screening.pipeline import screen_track_a, screen_track_b

PASSING_TRACK_A_FIELDS = {
    "roe": 20,
    "roce": 22,
    "debt_to_equity": 0.4,
    "promoter_holding_pct": 55,
    "promoter_holding_trend_3y": 1.0,
    "profit_growth_5y": 18,
    "promoter_pledge_pct": 0,
    "ebit": 100,
    "net_working_capital_ex_cash_ex_debt": 200,
    "net_fixed_assets_ex_goodwill": 200,
    "enterprise_value": 900,
}


def test_screen_track_a_shortlists_clean_candidate_and_ranks_by_greenblatt():
    clean = CompanyRecord("CLEAN", "profile_1_standard", dict(PASSING_TRACK_A_FIELDS))
    weaker = CompanyRecord(
        "WEAKER",
        "profile_1_standard",
        dict(PASSING_TRACK_A_FIELDS, ebit=20, enterprise_value=2000, net_working_capital_ex_cash_ex_debt=800, net_fixed_assets_ex_goodwill=800),
    )
    results = screen_track_a([clean, weaker])

    clean_result = next(r for r in results if r.ticker == "CLEAN")
    weaker_result = next(r for r in results if r.ticker == "WEAKER")
    assert clean_result.excluded is False
    assert clean_result.cleared_stage1 is True
    assert weaker_result.excluded is False
    # CLEAN has a stronger ROC/EY profile, so it should rank ahead of WEAKER.
    assert results.index(clean_result) < results.index(weaker_result)


def test_screen_track_a_excludes_on_promoter_pledging_fail():
    fields = dict(PASSING_TRACK_A_FIELDS, promoter_pledge_pct=30)
    record = CompanyRecord("PLEDGED", "profile_1_standard", fields)
    results = screen_track_a([record])

    result = results[0]
    assert result.excluded is True
    assert any("promoter_pledging" in reason for reason in result.exclusion_reasons)


def test_screen_track_a_excludes_when_quality_gate_fails():
    fields = dict(PASSING_TRACK_A_FIELDS, roe=5)
    record = CompanyRecord("WEAK", "profile_1_standard", fields)
    results = screen_track_a([record])

    result = results[0]
    assert result.cleared_stage1 is False
    assert result.excluded is True


def test_screen_track_a_sorts_excluded_candidates_last():
    good = CompanyRecord("GOOD", "profile_1_standard", dict(PASSING_TRACK_A_FIELDS))
    bad = CompanyRecord("BAD", "profile_1_standard", dict(PASSING_TRACK_A_FIELDS, promoter_pledge_pct=50))
    results = screen_track_a([bad, good])
    assert [r.ticker for r in results] == ["GOOD", "BAD"]


def test_screen_track_b_shortlists_by_peg_ascending():
    cheap = CompanyRecord("CHEAP", "profile_1_standard", {"pe_ratio": 8, "profit_growth_5y": 25, "promoter_pledge_pct": 0})
    pricier = CompanyRecord("PRICIER", "profile_1_standard", {"pe_ratio": 18, "profit_growth_5y": 25, "promoter_pledge_pct": 0})
    results = screen_track_b([pricier, cheap])

    assert results[0].ticker == "CHEAP"
    assert results[0].excluded is False


def test_screen_track_b_excludes_on_hard_block():
    record = CompanyRecord("BADPLEDGE", "profile_1_standard", {"pe_ratio": 8, "profit_growth_5y": 25, "promoter_pledge_pct": 40})
    results = screen_track_b([record])
    assert results[0].excluded is True
