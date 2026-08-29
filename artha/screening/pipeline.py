"""Screening pipeline — plan.md §5.3-§5.4, implementation_plan.md Phase 2 exit
criterion: "a run produces a ranked shortlist per track, with every
exclusion explained and attributed to the rule that fired."
"""

from __future__ import annotations

from dataclasses import dataclass, field

from artha.screening.hard_blocks import (
    GreenblattRankResult,
    fatal_flaw_checklist,
    promoter_integrity_red_flags,
    rank_by_greenblatt,
)
from artha.screening.models import CompanyRecord, Outcome, ScreenResult
from artha.screening.track_a import clears_track_a_stage1, run_track_a_stage1
from artha.screening.track_b import clears_track_b_stage1, run_track_b_stage1


@dataclass(frozen=True)
class CandidateResult:
    ticker: str
    track: str
    cleared_stage1: bool
    stage1_screens: dict[str, ScreenResult]
    fatal_flaw_result: ScreenResult
    promoter_integrity_result: ScreenResult
    greenblatt: GreenblattRankResult | None
    excluded: bool
    exclusion_reasons: tuple[str, ...] = field(default_factory=tuple)
    pending_stage3_items: tuple[str, ...] = field(default_factory=tuple)
    insufficient_data_fields: tuple[str, ...] = field(default_factory=tuple)


def _hard_block_exclusions(fatal_flaw: ScreenResult, promoter_integrity: ScreenResult) -> tuple[str, ...]:
    """Only a definitive FAIL disqualifies at this stage — plan.md routes
    unresolved (NEEDS_STAGE_3) questions to Stage 3 verification, not to an
    automatic exclusion; a genuine "no" answer still ends the analysis.
    """
    reasons: list[str] = []
    for result in (fatal_flaw, promoter_integrity):
        for criterion in result.criteria:
            if criterion.outcome == Outcome.FAIL:
                reasons.append(f"{result.screen_name}: {criterion.name} ({criterion.detail})")
    return tuple(reasons)


def _pending_stage3(*results: ScreenResult) -> tuple[str, ...]:
    pending: list[str] = []
    for result in results:
        for criterion in result.criteria:
            if criterion.outcome == Outcome.NEEDS_STAGE_3:
                pending.append(f"{result.screen_name}: {criterion.name}")
    return tuple(dict.fromkeys(pending))


def _insufficient_data(*results: ScreenResult) -> tuple[str, ...]:
    fields: list[str] = []
    for result in results:
        fields.extend(result.missing_data_fields)
    return tuple(dict.fromkeys(fields))


def screen_track_a(records: list[CompanyRecord]) -> list[CandidateResult]:
    """Run Track A Stage 1 + Stage 2 (hard blocks + Greenblatt gate) over a
    universe and return a ranked shortlist (best Greenblatt combined rank
    first), with every exclusion attributed to the rule that fired.
    """
    greenblatt_ranks = rank_by_greenblatt(records)

    candidates: list[CandidateResult] = []
    for record in records:
        stage1 = run_track_a_stage1(record)
        cleared = clears_track_a_stage1(stage1)

        fatal_flaw = fatal_flaw_checklist(record)
        promoter_integrity = promoter_integrity_red_flags(record)
        hard_block_reasons = _hard_block_exclusions(fatal_flaw, promoter_integrity)

        stage1_fail_reasons = tuple(
            f"{result.screen_name}: {c.name} ({c.detail})"
            for name in ("quality_gate", "growth_gate")
            for result in (stage1[name],)
            for c in result.criteria
            if c.outcome == Outcome.FAIL
        )

        exclusion_reasons = hard_block_reasons + (stage1_fail_reasons if not cleared else ())
        excluded = bool(exclusion_reasons)

        greenblatt = greenblatt_ranks.get(record.ticker)

        candidates.append(
            CandidateResult(
                ticker=record.ticker,
                track="A",
                cleared_stage1=cleared,
                stage1_screens=stage1,
                fatal_flaw_result=fatal_flaw,
                promoter_integrity_result=promoter_integrity,
                greenblatt=greenblatt,
                excluded=excluded,
                exclusion_reasons=exclusion_reasons,
                pending_stage3_items=_pending_stage3(fatal_flaw, promoter_integrity, *stage1.values()),
                insufficient_data_fields=_insufficient_data(fatal_flaw, promoter_integrity, *stage1.values()),
            )
        )

    def _sort_key(c: CandidateResult) -> tuple[int, int, str]:
        if c.excluded or not c.cleared_stage1:
            return (2, 0, c.ticker)
        if c.greenblatt is not None:
            return (0, c.greenblatt.combined_rank, c.ticker)
        return (1, 0, c.ticker)  # cleared but unranked (Greenblatt inputs unavailable)

    return sorted(candidates, key=_sort_key)


def screen_track_b(
    records: list[CompanyRecord],
    *,
    sector_median_pe: dict[str, float] | None = None,
    entry_pe_percentile_5y: dict[str, float] | None = None,
) -> list[CandidateResult]:
    """Run Track B Stage 1 + Stage 2 over a universe. Track B has no
    single ranking metric across its three alternative screens (Lynch PEG,
    Davis, Kedia) — the shortlist is ordered by PEG (ascending, cheaper
    first) where computable, then unranked candidates by ticker.
    """
    sector_median_pe = sector_median_pe or {}
    entry_pe_percentile_5y = entry_pe_percentile_5y or {}

    candidates: list[CandidateResult] = []
    for record in records:
        stage1 = run_track_b_stage1(
            record,
            entry_pe_percentile_5y=entry_pe_percentile_5y.get(record.ticker),
            sector_median_pe=sector_median_pe.get(str(record.get("sector"))),
        )
        cleared = clears_track_b_stage1(stage1)

        fatal_flaw = fatal_flaw_checklist(record)
        promoter_integrity = promoter_integrity_red_flags(record)
        hard_block_reasons = _hard_block_exclusions(fatal_flaw, promoter_integrity)

        stage1_fail_reasons = ()
        if not cleared:
            stage1_fail_reasons = tuple(
                f"{result.screen_name}: none of the alternative Track B screens passed"
                for result in stage1.values()
            )[:1]  # one summary reason, not one per screen, since clearance is "any of"

        exclusion_reasons = hard_block_reasons + (stage1_fail_reasons if not cleared else ())
        excluded = bool(exclusion_reasons)

        candidates.append(
            CandidateResult(
                ticker=record.ticker,
                track="B",
                cleared_stage1=cleared,
                stage1_screens=stage1,
                fatal_flaw_result=fatal_flaw,
                promoter_integrity_result=promoter_integrity,
                greenblatt=None,  # Greenblatt is Track-agnostic ranking, applied separately if desired
                excluded=excluded,
                exclusion_reasons=exclusion_reasons,
                pending_stage3_items=_pending_stage3(fatal_flaw, promoter_integrity, *stage1.values()),
                insufficient_data_fields=_insufficient_data(fatal_flaw, promoter_integrity, *stage1.values()),
            )
        )

    def _sort_key(c: CandidateResult) -> tuple[int, float, str]:
        if c.excluded or not c.cleared_stage1:
            return (2, 0.0, c.ticker)
        peg_result = c.stage1_screens.get("lynch_peg")
        if peg_result is not None and peg_result.score is not None:
            return (0, peg_result.score, c.ticker)
        return (1, 0.0, c.ticker)

    return sorted(candidates, key=_sort_key)
