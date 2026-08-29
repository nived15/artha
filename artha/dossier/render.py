"""Render a Dossier to the markdown format plan.md §6 specifies.

Rendering is intentionally the *last* step and does not itself validate —
call artha.dossier.validator.validate_dossier first (Phase 3a's factory
does this before writing, per implementation_plan.md §4).
"""

from __future__ import annotations

from artha.dossier.schema import Citation, Dossier, DossierSection


def _render_citations(citations: tuple[Citation, ...]) -> str:
    if not citations:
        return ""
    lines = [f"  - `{c.doc_id}` p.{c.page}" + (f" — {c.note}" if c.note else "") for c in citations]
    return "\n" + "\n".join(lines)


def _render_section(number: int, section: DossierSection) -> str:
    body = section.content.strip() or "*(empty)*"
    return f"## {number}. {section.title}\n\n{body}\n{_render_citations(section.citations)}\n"


def render_markdown(dossier: Dossier) -> str:
    identity = dossier.identity
    parts: list[str] = []

    parts.append(f"# {identity.company} ({identity.ticker})\n")
    parts.append(
        "## 1. Identity\n\n"
        f"- Company: {identity.company}\n"
        f"- Ticker: {identity.ticker}\n"
        f"- Sector: {identity.sector}\n"
        f"- Arithmetic profile: {identity.arithmetic_profile}\n"
        f"- Track: {identity.track}\n"
        f"- Date: {identity.date}\n"
        f"- Pipeline run ID: {identity.pipeline_run_id}\n"
        f"- Data snapshot ID: {identity.snapshot_id}\n"
    )

    parts.append(_render_section(2, dossier.business_five_sentences))
    parts.append(_render_section(3, dossier.why_now))
    parts.append(_render_section(4, dossier.three_things_must_be_true))
    parts.append(_render_section(5, dossier.financial_evidence))
    parts.append(_render_section(6, dossier.fatal_flaw_checklist))
    parts.append(_render_section(7, dossier.valuation))
    parts.append(_render_section(8, dossier.buy_below_and_sizing))
    parts.append(_render_section(9, dossier.pre_mortem))
    parts.append(_render_section(10, dossier.kill_triggers))
    parts.append(_render_section(11, dossier.what_would_make_me_add_more))
    parts.append(_render_section(12, dossier.disconfirming_evidence))
    parts.append(_render_section(13, dossier.holding_period_and_tax))

    provenance = dossier.provenance
    parts.append(
        "## 14. Provenance\n\n"
        f"- Model: {provenance.model}\n"
        f"- Prompt version: {provenance.prompt_version}\n"
        f"- Documents read: {', '.join(provenance.documents_read) or '(none)'}\n"
        f"- Could not verify: {', '.join(provenance.could_not_verify) or '(nothing outstanding)'}\n"
    )

    gate15 = dossier.moat_understandability_gate
    checklist_lines = "\n".join(f"  - {name}: {'PASS' if ok else 'FAIL'}" for name, ok in gate15.understandability_checklist.items())
    parts.append(
        "## 15. Moat & Understandability Memo (Buffett & Munger) — GATE\n\n"
        f"- Gate outcome: {'PASS' if gate15.passed else 'FAIL'}\n"
        f"- Moat type: {gate15.moat_type}\n"
        f"- Moat evidence: {gate15.moat_evidence}\n"
        f"- Return trend: {gate15.return_trend_summary}\n"
        f"- Five-sentence test: {gate15.five_sentence_test_result}\n"
        f"- Understandability checklist:\n{checklist_lines}\n"
        f"- Inversion summary: {gate15.inversion_summary}\n"
        f"{_render_citations(gate15.citations)}\n"
    )

    qglp = dossier.qglp_scorecard
    evidence_lines = "\n".join(f"  - {letter}: {text}" for letter, text in qglp.evidence.items())
    parts.append(
        "## 16. QGLP Scorecard (Raamdeo Agrawal)\n\n"
        f"- Quality: {qglp.quality}/3\n"
        f"- Growth: {qglp.growth}/3\n"
        f"- Longevity: {qglp.longevity}/3\n"
        f"- Price: {qglp.price}/3\n"
        f"- Combined: {qglp.combined_score}/12\n"
        f"- Evidence:\n{evidence_lines}\n"
        f"{_render_citations(qglp.citations)}\n"
    )

    parts.append(_render_section(17, dossier.margin_of_safety_scuttlebutt))

    gate18 = dossier.integrity_gate
    parts.append(
        "## 18. Super-Investor Integrity Gate (Fisher Point 15 + Agrawal) — GATE\n\n"
        f"- Gate outcome: {'PASS' if gate18.passed else 'FAIL'}\n"
        f"- Promoter pledge flag: {gate18.promoter_pledge_flag}\n"
        f"- Declining holding flag: {gate18.declining_holding_flag}\n"
        f"- RPT/auditor/SEBI flag: {gate18.rpt_or_auditor_or_sebi_flag}\n"
        f"- Evidence: {gate18.evidence}\n"
        f"{_render_citations(gate18.citations)}\n"
    )

    if dossier.davis_double_play is not None:
        parts.append(_render_section(19, dossier.davis_double_play))

    parts.append(_render_section(20, dossier.scale_economies_shared))
    parts.append(_render_section(21, dossier.magic_formula_attribution))

    if dossier.quality_compounding_checklist is not None:
        parts.append(_render_section(22, dossier.quality_compounding_checklist))

    parts.append(_render_section(23, dossier.conviction_sizing))

    if dossier.canslim_notes is not None:
        parts.append(_render_section(24, dossier.canslim_notes))

    return "\n".join(parts)
