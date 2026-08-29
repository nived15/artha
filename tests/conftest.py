"""Shared pytest fixtures."""

from __future__ import annotations

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
)

_CITATION = Citation("ANNUAL_REPORT_2024", 12, "MD&A")


def _section(title: str, *, cited: bool = True) -> DossierSection:
    return DossierSection(title=title, content=f"Evidence for {title}.", citations=(_CITATION,) if cited else ())


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
