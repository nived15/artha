"""Dossier completeness + citation-presence validator — plan.md §6.

"Sections 12 and 14 are the anti-self-deception mechanism. A dossier
missing either is rejected by the tooling, not by your discipline." This
validator embodies that line literally: it rejects, it does not warn.
`validate_dossier` never raises for a defective dossier — it returns a
`ValidationResult` whose `passed` is False and whose `errors` name every
defect, so a caller (a human, or Phase 3a's `validate_dossier` tool) gets
the full list in one pass rather than fixing one defect at a time.

This checks **completeness and citation-presence, not truth** —
implementation_plan.md §4 is explicit that this is "the non-negotiable
backstop regardless of how much agent-side verification is added," not a
substitute for it. A well-cited dossier can still be wrong; this module
only catches a dossier that skipped its own required evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from artha.dossier.schema import Dossier, DossierSection

# Evidence sections plan.md §6 requires "every figure with a source
# citation" for — each must carry at least one Citation.
_SECTIONS_REQUIRING_CITATIONS: tuple[str, ...] = (
    "financial_evidence",
    "fatal_flaw_checklist",
    "valuation",
    "margin_of_safety_scuttlebutt",
    "scale_economies_shared",
    "magic_formula_attribution",
    "conviction_sizing",
)

_TRACK_CONDITIONAL_SECTIONS: tuple[str, ...] = (
    "davis_double_play",
    "quality_compounding_checklist",
    "canslim_notes",
)

# section_name -> the track it is *required* for; the other track must
# leave it None (plan.md §6.24: "omitted for Track A").
_REQUIRED_FOR_TRACK: dict[str, str] = {
    "davis_double_play": "B",
    "quality_compounding_checklist": "A",
    "canslim_notes": "B",
}


@dataclass(frozen=True)
class ValidationError:
    section: str
    reason: str


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    errors: tuple[ValidationError, ...]

    def __bool__(self) -> bool:
        return self.passed


def _check_narrative_section(name: str, section: DossierSection, *, require_citations: bool) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if not section.content.strip():
        errors.append(ValidationError(name, "section content is empty"))
    if require_citations and not section.citations:
        errors.append(ValidationError(name, "no citations — plan.md §6 requires a source citation for every figure"))
    return errors


def validate_dossier(dossier: Dossier) -> ValidationResult:
    errors: list[ValidationError] = []

    errors += [ValidationError("identity", problem) for problem in dossier.identity.validate()]

    narrative_sections = {
        "business_five_sentences": dossier.business_five_sentences,
        "why_now": dossier.why_now,
        "three_things_must_be_true": dossier.three_things_must_be_true,
        "financial_evidence": dossier.financial_evidence,
        "fatal_flaw_checklist": dossier.fatal_flaw_checklist,
        "valuation": dossier.valuation,
        "buy_below_and_sizing": dossier.buy_below_and_sizing,
        "pre_mortem": dossier.pre_mortem,
        "kill_triggers": dossier.kill_triggers,
        "what_would_make_me_add_more": dossier.what_would_make_me_add_more,
        "holding_period_and_tax": dossier.holding_period_and_tax,
        "margin_of_safety_scuttlebutt": dossier.margin_of_safety_scuttlebutt,
        "scale_economies_shared": dossier.scale_economies_shared,
        "magic_formula_attribution": dossier.magic_formula_attribution,
        "conviction_sizing": dossier.conviction_sizing,
    }
    for name, section in narrative_sections.items():
        errors += _check_narrative_section(name, section, require_citations=name in _SECTIONS_REQUIRING_CITATIONS)

    # Section 12 — mandatory, and specifically must not be empty ("An
    # empty section fails review," plan.md §6). Citations are required too:
    # disconfirming evidence is still evidence.
    errors += _check_narrative_section("disconfirming_evidence", dossier.disconfirming_evidence, require_citations=True)

    # Section 14 — Provenance is mandatory and structured; every field must
    # be explicitly supplied (an empty model/prompt_version is a defect,
    # but an empty could_not_verify tuple is a valid claim, not a defect).
    provenance = dossier.provenance
    if not provenance.model.strip():
        errors.append(ValidationError("provenance", "model must not be empty"))
    if not provenance.prompt_version.strip():
        errors.append(ValidationError("provenance", "prompt_version must not be empty"))
    if not provenance.documents_read:
        errors.append(ValidationError("provenance", "documents_read must list at least one document"))

    # Section 15 — Moat & Understandability gate. A fail here is reported
    # distinctly from "missing data": the section is present and complete,
    # but the gate itself did not clear.
    gate15 = dossier.moat_understandability_gate
    if not gate15.moat_evidence.strip():
        errors.append(ValidationError("moat_understandability_gate", "moat_evidence is empty"))
    if not gate15.five_sentence_test_result.strip():
        errors.append(ValidationError("moat_understandability_gate", "five_sentence_test_result is empty"))
    if len(gate15.understandability_checklist) < 7:
        errors.append(ValidationError("moat_understandability_gate", "understandability_checklist must cover all 7 gates"))
    if not gate15.citations:
        errors.append(ValidationError("moat_understandability_gate", "no citations"))
    if not gate15.passed:
        errors.append(ValidationError("moat_understandability_gate", "gate failed — plan.md §6: halts the dossier before later sections"))

    # Section 16 — QGLP Scorecard.
    qglp = dossier.qglp_scorecard
    errors += [ValidationError("qglp_scorecard", p) for p in qglp.validate()]
    if len(qglp.evidence) < 4:
        errors.append(ValidationError("qglp_scorecard", "evidence must cover all four letters (Q/G/L/P)"))
    if not qglp.citations:
        errors.append(ValidationError("qglp_scorecard", "no citations"))

    # Section 18 — Super-Investor Integrity gate.
    gate18 = dossier.integrity_gate
    if not gate18.evidence.strip():
        errors.append(ValidationError("integrity_gate", "evidence is empty"))
    if not gate18.citations:
        errors.append(ValidationError("integrity_gate", "no citations"))
    if not gate18.passed:
        errors.append(ValidationError("integrity_gate", "gate failed — management integrity is a single-point-of-failure (plan.md §6)"))

    # Track-conditional sections: required for one track, must be absent
    # for the other.
    for name in _TRACK_CONDITIONAL_SECTIONS:
        section = getattr(dossier, name)
        required_track = _REQUIRED_FOR_TRACK[name]
        if dossier.identity.track == required_track:
            if section is None:
                errors.append(ValidationError(name, f"required for Track {required_track} but missing"))
            else:
                errors += _check_narrative_section(name, section, require_citations=True)
        elif section is not None:
            errors.append(ValidationError(name, f"must be omitted for Track {dossier.identity.track} (plan.md §6)"))

    return ValidationResult(passed=not errors, errors=tuple(errors))
