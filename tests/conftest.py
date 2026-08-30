"""Shared pytest fixtures."""

from __future__ import annotations

import dataclasses

import pytest

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

_CITATION = Citation("ANNUAL_REPORT_2024", 12, "MD&A")


def _section(title: str, *, cited: bool = True) -> DossierSection:
    return DossierSection(title=title, content=f"Evidence for {title}.", citations=(_CITATION,) if cited else ())


def make_return_assessment(track: str = "A") -> ReturnAssessment:
    scenarios = (
        (
            ScenarioLine("bear", 0.30, -0.475),
            ScenarioLine("base", 0.45, 0.35),
            ScenarioLine("bull", 0.25, 1.94),
        )
        if track == "B"
        else ()
    )
    return ReturnAssessment(
        track=track,
        horizon_years=5.0 if track == "A" else 3.0,
        gross_cagr=0.1932,
        net_cagr=0.1752,
        confidence=0.85,
        components={"growth": 0.1269, "carry": 0.01, "rerating": 0.06},
        spec_version="v1",
        spec_fingerprint="d8cdfd22fafd5f3b",
        scenarios=scenarios,
        asymmetry_ratio=4.08 if track == "B" else None,
        gates_passed=("liquidity", "promoter_pledge", "promoter_holding", "solvency"),
    )


def make_valid_dossier(track: str = "A") -> Dossier:
    """A minimally-complete, fully-valid Dossier for one track.

    Every section that plan.md §6 requires is populated; track-conditional
    sections are set/omitted to match `track`.
    """
    understandability_checklist = {
        "five_sentence_business_model": True,
        "unit_economics_clarity": True,
        "industry_structure_stability": True,
        "demand_forecastability_5_10yr": True,
        "management_understandability": True,
        "accounting_transparency": True,
        "identifiable_moat_source": True,
    }

    return Dossier(
        identity=Identity(
            company="Alpha Ltd",
            ticker="ALPHA",
            sector="Auto Ancillaries",
            arithmetic_profile="profile_1_standard",
            track=track,
            date="2026-01-15",
            pipeline_run_id="run-001",
            snapshot_id="deadbeef",
        ),
        business_five_sentences=_section("The business in five sentences"),
        why_now=_section("Why now"),
        three_things_must_be_true=_section("The three things that must be true"),
        financial_evidence=_section("Financial evidence"),
        fatal_flaw_checklist=_section("Fatal-flaw checklist"),
        valuation=_section("Valuation"),
        buy_below_and_sizing=_section("Buy-below price and sizing"),
        pre_mortem=_section("Pre-mortem"),
        kill_triggers=_section("Kill triggers"),
        what_would_make_me_add_more=_section("What would make me add more"),
        holding_period_and_tax=_section("Expected holding period and tax line"),
        disconfirming_evidence=_section("Disconfirming evidence"),
        provenance=Provenance(
            model="claude-opus",
            prompt_version="v1",
            documents_read=("ANNUAL_REPORT_2024",),
            could_not_verify=(),
        ),
        return_assessment=make_return_assessment(track),
        moat_understandability_gate=MoatUnderstandabilityGate(
            passed=True,
            moat_type="brand",
            moat_evidence="Strong brand recall in tier-2 cities.",
            return_trend_summary="ROE sustained above 18% for 8 of last 10 years.",
            five_sentence_test_result="Pass — business model is a simple auto-ancillary manufacturer.",
            understandability_checklist=understandability_checklist,
            inversion_summary="Would fail if a large OEM customer switched suppliers.",
            citations=(_CITATION,),
        ),
        qglp_scorecard=QGLPScorecard(
            quality=2,
            growth=2,
            longevity=2,
            price=1,
            evidence={"Q": "ROE 18%", "G": "PAT CAGR 16%", "L": "10yr track record", "P": "fair P/E"},
            citations=(_CITATION,),
        ),
        margin_of_safety_scuttlebutt=_section("Margin-of-Safety & Scuttlebutt Notes"),
        integrity_gate=IntegrityGate(
            passed=True,
            promoter_pledge_flag=False,
            declining_holding_flag=False,
            rpt_or_auditor_or_sebi_flag=False,
            evidence="No pledging; no adverse RPT/auditor/SEBI signals found.",
            citations=(_CITATION,),
        ),
        scale_economies_shared=_section("Scale Economies Shared Assessment"),
        magic_formula_attribution=_section("Magic Formula Attribution"),
        conviction_sizing=_section("Super-Investor Alignment / Conviction Sizing"),
        davis_double_play=_section("The Davis Double Play Mechanism") if track == "B" else None,
        quality_compounding_checklist=_section("Quality-Compounding Checklist") if track == "A" else None,
        canslim_notes=_section("CANSLIM Momentum Screen Notes") if track == "B" else None,
    )


@pytest.fixture
def valid_dossier_track_a() -> Dossier:
    return make_valid_dossier("A")


@pytest.fixture
def valid_dossier_track_b() -> Dossier:
    return make_valid_dossier("B")


def dossier_to_dict(dossier: Dossier) -> dict:
    """Convert a Dossier to a plain dict (mirrors an agent's structured
    JSON tool-call output) for round-trip/CLI tests."""

    def section(s):
        if s is None:
            return None
        return {"title": s.title, "content": s.content, "citations": [dataclasses.asdict(c) for c in s.citations]}

    return {
        "identity": dataclasses.asdict(dossier.identity),
        "business_five_sentences": section(dossier.business_five_sentences),
        "why_now": section(dossier.why_now),
        "three_things_must_be_true": section(dossier.three_things_must_be_true),
        "financial_evidence": section(dossier.financial_evidence),
        "fatal_flaw_checklist": section(dossier.fatal_flaw_checklist),
        "valuation": section(dossier.valuation),
        "buy_below_and_sizing": section(dossier.buy_below_and_sizing),
        "pre_mortem": section(dossier.pre_mortem),
        "kill_triggers": section(dossier.kill_triggers),
        "what_would_make_me_add_more": section(dossier.what_would_make_me_add_more),
        "holding_period_and_tax": section(dossier.holding_period_and_tax),
        "disconfirming_evidence": section(dossier.disconfirming_evidence),
        "provenance": dataclasses.asdict(dossier.provenance),
        "return_assessment": dataclasses.asdict(dossier.return_assessment),
        "moat_understandability_gate": dataclasses.asdict(dossier.moat_understandability_gate),
        "qglp_scorecard": dataclasses.asdict(dossier.qglp_scorecard),
        "margin_of_safety_scuttlebutt": section(dossier.margin_of_safety_scuttlebutt),
        "integrity_gate": dataclasses.asdict(dossier.integrity_gate),
        "scale_economies_shared": section(dossier.scale_economies_shared),
        "magic_formula_attribution": section(dossier.magic_formula_attribution),
        "conviction_sizing": section(dossier.conviction_sizing),
        "davis_double_play": section(dossier.davis_double_play),
        "quality_compounding_checklist": section(dossier.quality_compounding_checklist),
        "canslim_notes": section(dossier.canslim_notes),
    }
