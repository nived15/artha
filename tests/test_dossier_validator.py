from __future__ import annotations

import dataclasses

from artha.dossier.schema import DossierSection
from artha.dossier.validator import validate_dossier
from tests.conftest import make_valid_dossier


def test_valid_track_a_dossier_passes(valid_dossier_track_a):
    result = validate_dossier(valid_dossier_track_a)
    assert result.passed is True
    assert result.errors == ()
    assert bool(result) is True


def test_valid_track_b_dossier_passes(valid_dossier_track_b):
    result = validate_dossier(valid_dossier_track_b)
    assert result.passed is True


def test_empty_disconfirming_evidence_fails():
    dossier = make_valid_dossier("A")
    dossier = dataclasses.replace(dossier, disconfirming_evidence=DossierSection("Disconfirming evidence", ""))
    result = validate_dossier(dossier)
    assert result.passed is False
    assert any(e.section == "disconfirming_evidence" for e in result.errors)


def test_missing_provenance_documents_read_fails():
    dossier = make_valid_dossier("A")
    dossier = dataclasses.replace(dossier, provenance=dataclasses.replace(dossier.provenance, documents_read=()))
    result = validate_dossier(dossier)
    assert any(e.section == "provenance" for e in result.errors)


def test_empty_could_not_verify_is_not_an_error():
    # An empty could_not_verify list is a valid claim ("everything was
    # verified"), not a defect.
    dossier = make_valid_dossier("A")
    assert dossier.provenance.could_not_verify == ()
    result = validate_dossier(dossier)
    assert result.passed is True


def test_financial_evidence_without_citations_fails():
    dossier = make_valid_dossier("A")
    dossier = dataclasses.replace(dossier, financial_evidence=DossierSection("Financial evidence", "Revenue grew 20%.", ()))
    result = validate_dossier(dossier)
    assert any(e.section == "financial_evidence" and "citation" in e.reason for e in result.errors)


def test_moat_gate_failure_is_reported():
    dossier = make_valid_dossier("A")
    dossier = dataclasses.replace(dossier, moat_understandability_gate=dataclasses.replace(dossier.moat_understandability_gate, passed=False))
    result = validate_dossier(dossier)
    assert any(e.section == "moat_understandability_gate" and "gate failed" in e.reason for e in result.errors)


def test_integrity_gate_failure_is_reported():
    dossier = make_valid_dossier("A")
    dossier = dataclasses.replace(dossier, integrity_gate=dataclasses.replace(dossier.integrity_gate, passed=False))
    result = validate_dossier(dossier)
    assert any(e.section == "integrity_gate" and "gate failed" in e.reason for e in result.errors)


def test_qglp_scorecard_out_of_range_fails():
    dossier = make_valid_dossier("A")
    dossier = dataclasses.replace(dossier, qglp_scorecard=dataclasses.replace(dossier.qglp_scorecard, quality=5))
    result = validate_dossier(dossier)
    assert any(e.section == "qglp_scorecard" for e in result.errors)


def test_track_a_requires_quality_compounding_checklist():
    dossier = make_valid_dossier("A")
    dossier = dataclasses.replace(dossier, quality_compounding_checklist=None)
    result = validate_dossier(dossier)
    assert any(e.section == "quality_compounding_checklist" and "required for Track A" in e.reason for e in result.errors)


def test_track_a_must_omit_davis_and_canslim():
    dossier = make_valid_dossier("A")
    dossier = dataclasses.replace(dossier, davis_double_play=DossierSection("The Davis Double Play Mechanism", "x", ()))
    result = validate_dossier(dossier)
    assert any(e.section == "davis_double_play" and "must be omitted" in e.reason for e in result.errors)


def test_track_b_requires_davis_and_canslim():
    dossier = make_valid_dossier("B")
    dossier = dataclasses.replace(dossier, davis_double_play=None, canslim_notes=None)
    result = validate_dossier(dossier)
    sections_with_errors = {e.section for e in result.errors}
    assert "davis_double_play" in sections_with_errors
    assert "canslim_notes" in sections_with_errors


def test_track_b_must_omit_quality_compounding_checklist():
    dossier = make_valid_dossier("B")
    dossier = dataclasses.replace(dossier, quality_compounding_checklist=DossierSection("Quality-Compounding Checklist", "x", ()))
    result = validate_dossier(dossier)
    assert any(e.section == "quality_compounding_checklist" and "must be omitted" in e.reason for e in result.errors)


def test_invalid_identity_track_fails():
    dossier = make_valid_dossier("A")
    bad_identity = dataclasses.replace(dossier.identity, track="C")
    dossier = dataclasses.replace(dossier, identity=bad_identity)
    result = validate_dossier(dossier)
    assert any(e.section == "identity" for e in result.errors)


def test_empty_identity_field_fails():
    dossier = make_valid_dossier("A")
    bad_identity = dataclasses.replace(dossier.identity, company="")
    dossier = dataclasses.replace(dossier, identity=bad_identity)
    result = validate_dossier(dossier)
    assert any(e.section == "identity" and "company" in e.reason for e in result.errors)
