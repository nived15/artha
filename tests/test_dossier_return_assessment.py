from __future__ import annotations

import dataclasses

import pytest

from artha.dossier.quant import NotRankableError, return_assessment_from_candidate
from artha.dossier.render import render_markdown
from artha.dossier.schema import ScenarioLine
from artha.dossier.serialization import DossierSchemaError, dossier_from_dict
from artha.dossier.validator import validate_dossier
from artha.engine.features import build_feature_vector
from artha.engine.ranking import evaluate
from artha.engine.spec import FormulaSpec
from tests.conftest import dossier_to_dict, make_valid_dossier

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


def _assessment(track: str = "A", **overrides):
    spec = FormulaSpec()
    candidate = evaluate(_fv(), spec, track=track)
    built = return_assessment_from_candidate(
        candidate, spec_version=spec.version, spec_fingerprint=spec.fingerprint
    )
    return dataclasses.replace(built, **overrides) if overrides else built


# --- engine to dossier bridge -----------------------------------------------


def test_assessment_is_built_from_a_real_ranking_run():
    spec = FormulaSpec()
    assessment = _assessment("A")
    assert assessment.track == "A"
    assert assessment.spec_fingerprint == spec.fingerprint
    assert assessment.net_cagr < assessment.gross_cagr
    assert "growth" in assessment.components


def test_track_b_assessment_carries_its_scenario_tree():
    assessment = _assessment("B")
    assert [s.name for s in assessment.scenarios] == ["bear", "base", "bull"]
    assert assessment.asymmetry_ratio is not None


def test_a_rejected_candidate_cannot_produce_an_assessment():
    spec = FormulaSpec()
    rejected = evaluate(_fv(promoter_pledge=40.0), spec, track="A")
    with pytest.raises(NotRankableError, match="rejected"):
        return_assessment_from_candidate(rejected, spec_version=spec.version, spec_fingerprint=spec.fingerprint)


def test_an_unevaluable_candidate_cannot_produce_an_assessment():
    spec = FormulaSpec()
    unknown = evaluate(_fv(pe_ratio=None), spec, track="A")
    with pytest.raises(NotRankableError):
        return_assessment_from_candidate(unknown, spec_version=spec.version, spec_fingerprint=spec.fingerprint)


def test_pending_stage_1b_checks_are_carried_onto_the_assessment():
    # The bridge still carries the field; nothing populates it from a single
    # snapshot row now that OCF/PAT is gone.
    spec = FormulaSpec()
    candidate = evaluate(_fv(), spec, track="A")
    assessment = return_assessment_from_candidate(
        candidate, spec_version=spec.version, spec_fingerprint=spec.fingerprint
    )
    assert assessment.pending_verification == ()


# --- schema level validation ------------------------------------------------


def test_net_return_above_gross_is_rejected():
    problems = _assessment(gross_cagr=0.10, net_cagr=0.20).validate()
    assert any("exceeds gross" in p for p in problems)


def test_confidence_outside_zero_to_one_is_rejected():
    assert any("confidence" in p for p in _assessment(confidence=1.4).validate())


def test_missing_fingerprint_is_rejected():
    assert any("fingerprint" in p for p in _assessment(spec_fingerprint="  ").validate())


def test_gate_failure_on_the_assessment_is_rejected():
    problems = _assessment(gates_failed=("promoter_pledge",)).validate()
    assert any("gate-rejected" in p for p in problems)


def test_track_b_scenario_probabilities_must_sum_to_one():
    bad = _assessment(
        "B",
        scenarios=(ScenarioLine("bear", 0.3, -0.4), ScenarioLine("bull", 0.3, 1.9)),
    )
    assert any("sum to 1.0" in p for p in bad.validate())


# --- dossier level coherence ------------------------------------------------


def test_a_complete_dossier_still_validates():
    assert validate_dossier(make_valid_dossier("A")).passed is True
    assert validate_dossier(make_valid_dossier("B")).passed is True


def test_assessment_track_must_match_identity_track():
    dossier = make_valid_dossier("A")
    mismatched = dataclasses.replace(
        dossier, return_assessment=dataclasses.replace(dossier.return_assessment, track="B")
    )
    result = validate_dossier(mismatched)
    assert result.passed is False
    assert any("does not match identity.track" in e.reason for e in result.errors)


def test_unresolved_check_must_appear_in_could_not_verify():
    dossier = make_valid_dossier("A")
    with_pending = dataclasses.replace(
        dossier,
        return_assessment=dataclasses.replace(
            dossier.return_assessment,
            pending_verification=("multi_year_consistency: 10y ROE series unavailable",),
        ),
    )
    result = validate_dossier(with_pending)
    assert result.passed is False
    assert any("could_not_verify" in e.reason for e in result.errors)


def test_declaring_the_unresolved_check_in_provenance_satisfies_the_rule():
    dossier = make_valid_dossier("A")
    fixed = dataclasses.replace(
        dossier,
        return_assessment=dataclasses.replace(
            dossier.return_assessment,
            pending_verification=("multi_year_consistency: 10y ROE series unavailable",),
        ),
        provenance=dataclasses.replace(
            dossier.provenance,
            could_not_verify=("multi_year_consistency could not be confirmed from Stage 1a data",),
        ),
    )
    assert validate_dossier(fixed).passed is True


# --- serialization and rendering --------------------------------------------


def test_assessment_survives_a_json_round_trip():
    dossier = make_valid_dossier("B")
    parsed = dossier_from_dict(dossier_to_dict(dossier))
    assert parsed.return_assessment == dossier.return_assessment


def test_a_draft_without_an_assessment_names_the_injection_step():
    payload = dossier_to_dict(make_valid_dossier("A"))
    del payload["return_assessment"]
    with pytest.raises(DossierSchemaError, match="injected from a ranking run"):
        dossier_from_dict(payload)


def test_rendered_markdown_shows_the_return_and_its_fingerprint():
    markdown = render_markdown(make_valid_dossier("A"))
    assert "Quantitative Return Assessment" in markdown
    assert "d8cdfd22fafd5f3b" in markdown
    assert "post-tax" in markdown


def test_rendered_markdown_states_when_nothing_is_outstanding():
    assert "(nothing outstanding)" in render_markdown(make_valid_dossier("A"))
