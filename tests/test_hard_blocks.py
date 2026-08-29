from __future__ import annotations

import pytest

from artha.screening.hard_blocks import (
    DownsideFloorScore,
    company_to_greenblatt_inputs,
    fatal_flaw_checklist,
    pabrai_asymmetry_gate,
    promoter_integrity_red_flags,
    promoter_pledging_check,
    rank_by_greenblatt,
)
from artha.screening.models import CompanyRecord, Outcome


def _record(ticker: str, fields: dict, profile: str = "profile_1_standard") -> CompanyRecord:
    return CompanyRecord(ticker=ticker, arithmetic_profile=profile, fields=fields)


def test_promoter_pledging_fails_closed_when_unknown():
    criterion = promoter_pledging_check(_record("A", {}))
    assert criterion.outcome == Outcome.FAIL
    assert "fails closed" in criterion.detail


def test_promoter_pledging_passes_below_threshold():
    criterion = promoter_pledging_check(_record("A", {"promoter_pledge_pct": 5}))
    assert criterion.outcome == Outcome.PASS


def test_promoter_pledging_fails_above_threshold():
    criterion = promoter_pledging_check(_record("A", {"promoter_pledge_pct": 25}))
    assert criterion.outcome == Outcome.FAIL


def test_promoter_integrity_red_flags_fails_on_declining_holding():
    result = promoter_integrity_red_flags(_record("A", {"promoter_pledge_pct": 0, "promoter_holding_trend_3y": -1.0}))
    assert result.outcome == Outcome.FAIL


def test_fatal_flaw_checklist_reports_most_items_as_needs_stage_3():
    result = fatal_flaw_checklist(_record("A", {"promoter_pledge_pct": 0, "ocf_to_pat": 0.9}))
    stage3_items = [c for c in result.criteria if c.outcome == Outcome.NEEDS_STAGE_3]
    assert len(stage3_items) >= 5


def test_company_to_greenblatt_inputs_computes_roc_and_ey_for_profile_1():
    record = _record(
        "A",
        {
            "ebit": 100,
            "net_working_capital_ex_cash_ex_debt": 200,
            "net_fixed_assets_ex_goodwill": 300,
            "enterprise_value": 1000,
        },
    )
    inputs = company_to_greenblatt_inputs(record)
    assert inputs.roc_or_substitute == pytest.approx(100 / 500)
    assert inputs.earnings_yield == pytest.approx(100 / 1000)


def test_company_to_greenblatt_inputs_none_for_non_standard_profile():
    inputs = company_to_greenblatt_inputs(_record("A", {}, profile="profile_2_banking"))
    assert inputs.roc_or_substitute is None
    assert inputs.earnings_yield is None


def test_rank_by_greenblatt_ranks_best_decile():
    # 10 companies with increasing ROC and EY (company J is best on both).
    records = []
    for i, letter in enumerate("ABCDEFGHIJ"):
        ebit = 10 + i
        records.append(
            _record(
                letter,
                {
                    "ebit": ebit,
                    "net_working_capital_ex_cash_ex_debt": 50,
                    "net_fixed_assets_ex_goodwill": 50,
                    "enterprise_value": 100,
                },
            )
        )
    ranks = rank_by_greenblatt(records, best_decile_pct=10.0)
    assert ranks["J"].combined_rank == 2  # rank 1 on both ROC and EY
    assert ranks["J"].passed is True
    assert ranks["A"].passed is False


def test_rank_by_greenblatt_excludes_unrankable_companies():
    records = [_record("A", {}), _record("B", {"ebit": 10, "net_working_capital_ex_cash_ex_debt": 10, "net_fixed_assets_ex_goodwill": 10, "enterprise_value": 100})]
    ranks = rank_by_greenblatt(records)
    assert "A" not in ranks
    assert "B" in ranks


def test_downside_floor_score_validates_range():
    with pytest.raises(ValueError):
        DownsideFloorScore(5, 0, 0, 0)


def test_downside_floor_score_total():
    score = DownsideFloorScore(4, 3, 2, 1)
    assert score.total == 10


def test_pabrai_gate_passes_when_both_tests_clear():
    score = DownsideFloorScore(4, 3, 2, 1)  # total = 10
    result = pabrai_asymmetry_gate(score, bull_case_upside_pct=90, bear_case_downside_pct=25)
    assert result.downside_floor_passed is True
    assert result.asymmetry_ratio == pytest.approx(3.6)
    assert result.asymmetry_passed is True
    assert result.passed is True


def test_pabrai_gate_fails_if_either_test_fails():
    low_score = DownsideFloorScore(2, 2, 2, 2)  # total = 8, below 10
    result = pabrai_asymmetry_gate(low_score, bull_case_upside_pct=90, bear_case_downside_pct=25)
    assert result.downside_floor_passed is False
    assert result.passed is False

    good_score = DownsideFloorScore(4, 4, 4, 4)  # total = 16
    weak_asymmetry = pabrai_asymmetry_gate(good_score, bull_case_upside_pct=50, bear_case_downside_pct=25)
    assert weak_asymmetry.asymmetry_passed is False
    assert weak_asymmetry.passed is False


def test_pabrai_gate_rejects_non_positive_bear_case():
    score = DownsideFloorScore(4, 4, 4, 4)
    with pytest.raises(ValueError):
        pabrai_asymmetry_gate(score, bull_case_upside_pct=50, bear_case_downside_pct=0)
