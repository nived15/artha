"""The 24-section dossier data model — plan.md §6.

Two design choices, both deliberate:

1. **Track-conditional sections are typed as optional, not just "empty."**
   Davis Double Play (§19) and CANSLIM (§24) are Track B only; the Quality-
   Compounding Checklist (§22) is Track A only. Modeling them as
   `X | None` lets the validator distinguish "not applicable to this
   track" from "applicable but missing" — the latter is a defect, the
   former isn't.
2. **Every evidence section carries its own citations.** plan.md §6: "every
   figure with a source citation." `Citation(doc_id, page)` matches the
   citation-preserving chunk store's own key (artha.data.filings) so a
   dossier claim's citation is directly checkable against that store.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    """A citation into the filing chunk store (artha.data.filings): the
    exact (doc_id, page) a claim rests on — plan.md §5.5/§6's citation rule.
    """

    doc_id: str
    page: int
    note: str = ""


@dataclass(frozen=True)
class DossierSection:
    """A generic evidence/narrative section: free-text content plus the
    citations backing it. Used for sections whose structure plan.md does
    not otherwise specify beyond "written prose with cited evidence."
    """

    title: str
    content: str
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True)
class Identity:
    """§6.1 — Identity."""

    company: str
    ticker: str
    sector: str
    arithmetic_profile: str  # plan.md §5.3a
    track: str  # "A" or "B"
    date: str  # ISO date
    pipeline_run_id: str
    snapshot_id: str  # artha.data.snapshot's content-addressable snapshot_id

    def validate(self) -> list[str]:
        problems = []
        for name in ("company", "ticker", "sector", "arithmetic_profile", "date", "pipeline_run_id", "snapshot_id"):
            if not getattr(self, name).strip():
                problems.append(f"identity.{name} must not be empty")
        if self.track not in ("A", "B"):
            problems.append(f"identity.track must be 'A' or 'B', got {self.track!r}")
        return problems


@dataclass(frozen=True)
class MoatUnderstandabilityGate:
    """§6.15 — Moat & Understandability Memo (Buffett & Munger). A *gate*:
    a fail here halts the dossier before the remaining sections are
    written (plan.md §6)."""

    passed: bool
    moat_type: str  # brand / switching_cost / network_effect / cost_advantage / efficient_scale_regulatory / none
    moat_evidence: str
    return_trend_summary: str  # 10yr ROE/ROIC-vs-WACC, or the Profile 2-5 substitute series
    five_sentence_test_result: str
    understandability_checklist: dict[str, bool]  # the 7-gate checklist, keyed by gate name
    inversion_summary: str  # "what would make this fail" (Munger)
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True)
class QGLPScorecard:
    """§6.16 — QGLP Scorecard (Agrawal). Price is scored last, by design."""

    quality: int  # 0-3
    growth: int  # 0-3
    longevity: int  # 0-3
    price: int  # 0-3
    evidence: dict[str, str]  # letter ("Q"/"G"/"L"/"P") -> evidence text
    citations: tuple[Citation, ...] = ()

    @property
    def combined_score(self) -> int:
        return self.quality + self.growth + self.longevity + self.price

    def validate(self) -> list[str]:
        problems = []
        for letter, value in (("quality", self.quality), ("growth", self.growth), ("longevity", self.longevity), ("price", self.price)):
            if not 0 <= value <= 3:
                problems.append(f"qglp_scorecard.{letter} must be in [0, 3], got {value}")
        return problems


@dataclass(frozen=True)
class IntegrityGate:
    """§6.18 — Super-Investor Integrity Gate (Fisher Point 15 + Agrawal
    governance signals). A *gate*: management integrity is a single-point-
    of-failure the other 23 sections cannot compensate for (plan.md §6)."""

    passed: bool
    promoter_pledge_flag: bool  # True = a red flag fired (pledge > 20%, plan.md §5.4)
    declining_holding_flag: bool
    rpt_or_auditor_or_sebi_flag: bool
    evidence: str
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True)
class Provenance:
    """§6.14 — Provenance. Mandatory; an empty `could_not_verify` is a
    deliberate claim ("everything was verified"), not the absence of one —
    the field must always be supplied, even as an explicit empty tuple.
    """

    model: str
    prompt_version: str
    documents_read: tuple[str, ...]  # doc_ids from artha.data.filings
    could_not_verify: tuple[str, ...]


@dataclass(frozen=True)
class Dossier:
    """The full 24-section dossier for one candidate, one pipeline run."""

    identity: Identity

    # Sections 2-11, 13 — narrative/evidence sections.
    business_five_sentences: DossierSection
    why_now: DossierSection
    three_things_must_be_true: DossierSection
    financial_evidence: DossierSection
    fatal_flaw_checklist: DossierSection
    valuation: DossierSection
    buy_below_and_sizing: DossierSection
    pre_mortem: DossierSection
    kill_triggers: DossierSection
    what_would_make_me_add_more: DossierSection
    holding_period_and_tax: DossierSection

    # Section 12 — the anti-self-deception mechanism (mandatory, non-empty).
    disconfirming_evidence: DossierSection

    # Section 14 — the anti-self-deception mechanism (mandatory, structured).
    provenance: Provenance

    # Sections 15-24 — the framework sections (§17 sourcing).
    moat_understandability_gate: MoatUnderstandabilityGate  # §15, gate
    qglp_scorecard: QGLPScorecard  # §16
    margin_of_safety_scuttlebutt: DossierSection  # §17 (Graham + Fisher combined)
    integrity_gate: IntegrityGate  # §18, gate
    scale_economies_shared: DossierSection  # §20, both tracks
    magic_formula_attribution: DossierSection  # §21, both tracks
    conviction_sizing: DossierSection  # §23, both tracks (Pabrai + Jhunjhunwala)

    # Track-conditional sections — None means "not applicable to this
    # track," which the validator treats differently from "missing."
    davis_double_play: DossierSection | None = None  # §19, Track B only
    quality_compounding_checklist: DossierSection | None = None  # §22, Track A only
    canslim_notes: DossierSection | None = None  # §24, Track B only, omitted for Track A
