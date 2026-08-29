from __future__ import annotations

from artha.screening.models import CompanyRecord, Criterion, Outcome, overall_outcome


def test_company_record_get_float_parses_and_handles_missing():
    record = CompanyRecord(ticker="ALPHA", arithmetic_profile="profile_1_standard", fields={"roe": "18.5", "junk": "abc"})
    assert record.get_float("roe") == 18.5
    assert record.get_float("junk") is None
    assert record.get_float("missing") is None
    assert record.get("roe") == "18.5"


def test_overall_outcome_all_pass():
    criteria = (Criterion("a", Outcome.PASS, ""), Criterion("b", Outcome.PASS, ""))
    assert overall_outcome(criteria) == Outcome.PASS


def test_overall_outcome_fail_takes_precedence_over_needs_stage_1b():
    criteria = (Criterion("a", Outcome.FAIL, ""), Criterion("b", Outcome.NEEDS_STAGE_1B, ""))
    assert overall_outcome(criteria) == Outcome.FAIL


def test_overall_outcome_needs_stage_1b_when_no_fail():
    criteria = (Criterion("a", Outcome.PASS, ""), Criterion("b", Outcome.NEEDS_STAGE_1B, ""))
    assert overall_outcome(criteria) == Outcome.NEEDS_STAGE_1B


def test_overall_outcome_needs_stage_3_when_no_fail_or_1b():
    criteria = (Criterion("a", Outcome.PASS, ""), Criterion("b", Outcome.NEEDS_STAGE_3, ""))
    assert overall_outcome(criteria) == Outcome.NEEDS_STAGE_3


def test_overall_outcome_respects_mandatory_subset():
    criteria = (Criterion("a", Outcome.PASS, ""), Criterion("b", Outcome.FAIL, ""))
    assert overall_outcome(criteria, mandatory=("a",)) == Outcome.PASS


def test_overall_outcome_empty_criteria_is_not_applicable():
    assert overall_outcome(()) == Outcome.NOT_APPLICABLE
