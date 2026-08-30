"""JSON (de)serialization for the Dossier schema.

Agents produce structured JSON (the natural output shape for an LLM tool
call or schema-constrained subagent, per the Agent Factory's `ctx.agent`
`schema` option) — this module is the bridge between that JSON and the
Dossier dataclasses artha.dossier.validator/render/storage operate on.
"""

from __future__ import annotations

from typing import Any

from artha.dossier.schema import (
    Citation,
    Dossier,
    DossierSection,
    Identity,
    IntegrityGate,
    MoatUnderstandabilityGate,
    Provenance,
    QGLPScorecard,
    ReturnAssessment,
    ScenarioLine,
)


class DossierSchemaError(ValueError):
    """Raised when a JSON draft is structurally incompatible with Dossier."""


def _citations_from_list(raw: list[dict] | None) -> tuple[Citation, ...]:
    if not raw:
        return ()
    return tuple(Citation(doc_id=c["doc_id"], page=int(c["page"]), note=c.get("note", "")) for c in raw)


def _section_from_dict(data: dict) -> DossierSection:
    return DossierSection(
        title=data.get("title", ""),
        content=data.get("content", ""),
        citations=_citations_from_list(data.get("citations")),
    )


def _optional_section_from_dict(data: dict | None) -> DossierSection | None:
    return _section_from_dict(data) if data is not None else None


def _return_assessment_from_dict(raw: dict) -> ReturnAssessment:
    return ReturnAssessment(
        track=raw["track"],
        horizon_years=float(raw["horizon_years"]),
        gross_cagr=float(raw["gross_cagr"]),
        net_cagr=float(raw["net_cagr"]),
        confidence=float(raw["confidence"]),
        components={k: float(v) for k, v in raw.get("components", {}).items()},
        spec_version=raw.get("spec_version", ""),
        spec_fingerprint=raw.get("spec_fingerprint", ""),
        scenarios=tuple(
            ScenarioLine(s["name"], float(s["probability"]), float(s["total_return"]))
            for s in raw.get("scenarios", ())
        ),
        asymmetry_ratio=None if raw.get("asymmetry_ratio") is None else float(raw["asymmetry_ratio"]),
        gates_passed=tuple(raw.get("gates_passed", ())),
        gates_failed=tuple(raw.get("gates_failed", ())),
        pending_verification=tuple(raw.get("pending_verification", ())),
    )


def dossier_from_dict(data: dict[str, Any]) -> Dossier:
    """Parse a JSON-compatible dict (e.g. from an agent's structured output)
    into a Dossier. Raises DossierSchemaError for structurally missing
    required keys — this is a *parsing* error, distinct from
    validate_dossier's completeness/citation checks, which run on an
    already-parsed Dossier.
    """
    try:
        identity_raw = data["identity"]
        identity = Identity(
            company=identity_raw["company"],
            ticker=identity_raw["ticker"],
            sector=identity_raw["sector"],
            arithmetic_profile=identity_raw["arithmetic_profile"],
            track=identity_raw["track"],
            date=identity_raw["date"],
            pipeline_run_id=identity_raw["pipeline_run_id"],
            snapshot_id=identity_raw["snapshot_id"],
        )

        provenance_raw = data["provenance"]
        provenance = Provenance(
            model=provenance_raw.get("model", ""),
            prompt_version=provenance_raw.get("prompt_version", ""),
            documents_read=tuple(provenance_raw.get("documents_read", ())),
            could_not_verify=tuple(provenance_raw.get("could_not_verify", ())),
        )

        gate15_raw = data["moat_understandability_gate"]
        moat_gate = MoatUnderstandabilityGate(
            passed=bool(gate15_raw["passed"]),
            moat_type=gate15_raw.get("moat_type", ""),
            moat_evidence=gate15_raw.get("moat_evidence", ""),
            return_trend_summary=gate15_raw.get("return_trend_summary", ""),
            five_sentence_test_result=gate15_raw.get("five_sentence_test_result", ""),
            understandability_checklist=dict(gate15_raw.get("understandability_checklist", {})),
            inversion_summary=gate15_raw.get("inversion_summary", ""),
            citations=_citations_from_list(gate15_raw.get("citations")),
        )

        qglp_raw = data["qglp_scorecard"]
        qglp = QGLPScorecard(
            quality=int(qglp_raw["quality"]),
            growth=int(qglp_raw["growth"]),
            longevity=int(qglp_raw["longevity"]),
            price=int(qglp_raw["price"]),
            evidence=dict(qglp_raw.get("evidence", {})),
            citations=_citations_from_list(qglp_raw.get("citations")),
        )

        gate18_raw = data["integrity_gate"]
        integrity_gate = IntegrityGate(
            passed=bool(gate18_raw["passed"]),
            promoter_pledge_flag=bool(gate18_raw.get("promoter_pledge_flag", False)),
            declining_holding_flag=bool(gate18_raw.get("declining_holding_flag", False)),
            rpt_or_auditor_or_sebi_flag=bool(gate18_raw.get("rpt_or_auditor_or_sebi_flag", False)),
            evidence=gate18_raw.get("evidence", ""),
            citations=_citations_from_list(gate18_raw.get("citations")),
        )

        return Dossier(
            identity=identity,
            business_five_sentences=_section_from_dict(data["business_five_sentences"]),
            why_now=_section_from_dict(data["why_now"]),
            three_things_must_be_true=_section_from_dict(data["three_things_must_be_true"]),
            financial_evidence=_section_from_dict(data["financial_evidence"]),
            fatal_flaw_checklist=_section_from_dict(data["fatal_flaw_checklist"]),
            valuation=_section_from_dict(data["valuation"]),
            buy_below_and_sizing=_section_from_dict(data["buy_below_and_sizing"]),
            pre_mortem=_section_from_dict(data["pre_mortem"]),
            kill_triggers=_section_from_dict(data["kill_triggers"]),
            what_would_make_me_add_more=_section_from_dict(data["what_would_make_me_add_more"]),
            holding_period_and_tax=_section_from_dict(data["holding_period_and_tax"]),
            disconfirming_evidence=_section_from_dict(data["disconfirming_evidence"]),
            provenance=provenance,
            return_assessment=_return_assessment_from_dict(data["return_assessment"]),
            moat_understandability_gate=moat_gate,
            qglp_scorecard=qglp,
            margin_of_safety_scuttlebutt=_section_from_dict(data["margin_of_safety_scuttlebutt"]),
            integrity_gate=integrity_gate,
            scale_economies_shared=_section_from_dict(data["scale_economies_shared"]),
            magic_formula_attribution=_section_from_dict(data["magic_formula_attribution"]),
            conviction_sizing=_section_from_dict(data["conviction_sizing"]),
            davis_double_play=_optional_section_from_dict(data.get("davis_double_play")),
            quality_compounding_checklist=_optional_section_from_dict(data.get("quality_compounding_checklist")),
            canslim_notes=_optional_section_from_dict(data.get("canslim_notes")),
        )
    except KeyError as exc:
        if str(exc).strip("'") == "return_assessment":
            raise DossierSchemaError(
                "dossier draft missing 'return_assessment' — this section is injected from a "
                "ranking run via artha.dossier.quant.return_assessment_from_candidate, not authored"
            ) from exc
        raise DossierSchemaError(f"dossier draft missing required key: {exc}") from exc
