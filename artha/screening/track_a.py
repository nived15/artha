"""Track A (compounders) Stage 1a screens — plan.md §5.3, §5.3a.

Mandatory gates (Agrawal QGLP "Q" and "G") decide whether a name clears
Stage 1 for Track A. The moat/quality refinement and Graham defensive
criteria are explicitly *non-gating* per plan.md's own wording ("for the
highest-conviction subset"; "optional qualifying screen") — they are
scored and attributed, feeding later dossier sections (§6.16-17), but do
not by themselves exclude a name from the ranked Stage 1 shortlist.
"""

from __future__ import annotations

from artha.screening.models import Criterion, Outcome, ScreenResult, CompanyRecord, overall_outcome

# Profile 2 (lending) drops D/E, ROCE, OCF/PAT, EBIT and EV-based metrics
# as meaningless (plan.md §5.3a) — the quality gate substitutes ROA/NIM
# fields that Phase 2 does not yet screen (tracked as Stage 1b/Phase-2
# follow-up); Profile 1 is the only profile this module fully screens.
_STANDARD_PROFILE = "profile_1_standard"


def quality_gate(record: CompanyRecord) -> ScreenResult:
    """Agrawal QGLP "Q": ROE >= 15%, ROCE >= 15% (ideal >=20%), D/E <= 1.0,
    promoter holding >= 50% and not declining.

    OCF/PAT is not exportable from Screener, so cash conversion is assessed
    from filings at Stage 3 rather than screened here."""
    criteria: list[Criterion] = []

    if record.arithmetic_profile != _STANDARD_PROFILE:
        criteria.append(
            Criterion(
                "quality_gate_profile_support",
                Outcome.NOT_APPLICABLE,
                f"Quality gate arithmetic is Profile 1-only; {record.arithmetic_profile} needs its own "
                "substitute ratios (plan.md §5.3a) — not yet implemented.",
            )
        )
        return ScreenResult("QGLP Quality Gate", "A", Outcome.NOT_APPLICABLE, tuple(criteria))

    roe = record.get_float("roe")
    criteria.append(
        Criterion(
            "roe_at_least_15",
            Outcome.PASS if roe is not None and roe >= 15 else (Outcome.FAIL if roe is not None else Outcome.NEEDS_STAGE_1B),
            f"ROE={roe}" if roe is not None else "roe missing",
            ("roe",),
        )
    )

    roce = record.get_float("roce")
    criteria.append(
        Criterion(
            "roce_at_least_15",
            Outcome.PASS if roce is not None and roce >= 15 else (Outcome.FAIL if roce is not None else Outcome.NEEDS_STAGE_1B),
            f"ROCE={roce}" if roce is not None else "roce missing",
            ("roce",),
        )
    )

    de = record.get_float("debt_to_equity")
    criteria.append(
        Criterion(
            "debt_to_equity_at_most_1",
            Outcome.PASS if de is not None and de <= 1.0 else (Outcome.FAIL if de is not None else Outcome.NEEDS_STAGE_1B),
            f"D/E={de}" if de is not None else "debt_to_equity missing",
            ("debt_to_equity",),
        )
    )

    promoter = record.get_float("promoter_holding_pct")
    trend = record.get_float("promoter_holding_trend_3y")
    if promoter is None:
        promoter_outcome = Outcome.NEEDS_STAGE_1B
        detail = "promoter_holding_pct missing"
    elif promoter < 50:
        promoter_outcome = Outcome.FAIL
        detail = f"promoter_holding_pct={promoter} < 50"
    elif trend is not None and trend < 0:
        promoter_outcome = Outcome.FAIL
        detail = f"promoter_holding_pct={promoter} but declining (3yr trend={trend})"
    else:
        promoter_outcome = Outcome.PASS
        detail = f"promoter_holding_pct={promoter}, 3yr trend={trend}"
    criteria.append(Criterion("promoter_holding_ge_50_not_declining", promoter_outcome, detail, ("promoter_holding_pct", "promoter_holding_trend_3y")))

    outcome = overall_outcome(tuple(criteria))
    return ScreenResult("QGLP Quality Gate", "A", outcome, tuple(criteria))


def growth_gate(record: CompanyRecord) -> ScreenResult:
    """Agrawal QGLP "G": PAT CAGR >= 15% over 5 years (ideal >=20%).

    "No year of EPS decline" is explicitly a Stage 1b own-history test
    (plan.md §13) — a single snapshot row cannot answer it, so it is
    reported as needing Stage 1b rather than assumed true.
    """
    criteria: list[Criterion] = []

    pat_cagr = record.get_float("profit_growth_5y")
    criteria.append(
        Criterion(
            "pat_cagr_5y_at_least_15",
            Outcome.PASS if pat_cagr is not None and pat_cagr >= 15 else (Outcome.FAIL if pat_cagr is not None else Outcome.NEEDS_STAGE_1B),
            f"5yr PAT CAGR={pat_cagr}" if pat_cagr is not None else "profit_growth_5y missing",
            ("profit_growth_5y",),
        )
    )
    criteria.append(
        Criterion(
            "no_year_of_eps_decline",
            Outcome.NEEDS_STAGE_1B,
            "own-history, year-by-year EPS test — plan.md §13 assigns this to Stage 1b, not Stage 1a",
            (),
        )
    )

    outcome = overall_outcome(tuple(criteria), mandatory=("pat_cagr_5y_at_least_15",))
    return ScreenResult("QGLP Growth Gate", "A", outcome, tuple(criteria))


def moat_quality_refinement(record: CompanyRecord) -> ScreenResult:
    """Buffett & Munger / Terry Smith moat/quality refinement — non-gating.

    plan.md: "for the highest-conviction subset, gross margin >= 50%,
    ROCE >= 20%, interest cover >= 10x, FCF conversion >= 80%." The
    "ROE/ROIC sustained >=15 of the last 10 years above WACC" clause is a
    Stage 1b multi-year test.
    """
    criteria: list[Criterion] = [
        Criterion(
            "roe_roic_sustained_10y",
            Outcome.NEEDS_STAGE_1B,
            "10-year sustained ROE/ROIC-vs-WACC — Stage 1b own-history test",
            (),
        )
    ]

    def _threshold(key: str, floor: float, label: str) -> Criterion:
        value = record.get_float(key)
        if value is None:
            return Criterion(label, Outcome.NEEDS_STAGE_1B, f"{key} missing", (key,))
        return Criterion(label, Outcome.PASS if value >= floor else Outcome.FAIL, f"{key}={value}", (key,))

    criteria.append(_threshold("gross_margin", 50, "gross_margin_at_least_50"))
    criteria.append(_threshold("roce", 20, "roce_at_least_20"))
    criteria.append(_threshold("interest_coverage", 10, "interest_coverage_at_least_10"))
    criteria.append(_threshold("fcf_conversion_pct", 80, "fcf_conversion_at_least_80"))

    # Non-gating refinement: report the composite outcome for visibility,
    # but callers should not exclude a name from Stage 1 on this alone.
    outcome = overall_outcome(tuple(criteria))
    return ScreenResult("Moat/Quality Refinement", "A", outcome, tuple(criteria))


def graham_defensive_criteria(record: CompanyRecord) -> ScreenResult:
    """Graham's defensive-investor criteria, thresholds relaxed per plan.md §17
    for the Indian listing base — non-gating ("optional qualifying screen").
    """
    criteria: list[Criterion] = []

    cr = record.get_float("current_ratio")
    criteria.append(
        Criterion(
            "current_ratio_at_least_2",
            Outcome.PASS if cr is not None and cr >= 2.0 else (Outcome.FAIL if cr is not None else Outcome.NEEDS_STAGE_1B),
            f"current_ratio={cr}" if cr is not None else "current_ratio missing",
            ("current_ratio",),
        )
    )
    criteria.append(
        Criterion(
            "no_earnings_deficit_10y",
            Outcome.NEEDS_STAGE_1B,
            "10-year earnings-deficit test — plan.md §13 assigns this to Stage 1b",
            (),
        )
    )

    pe = record.get_float("pe_ratio")
    criteria.append(
        Criterion(
            "pe_at_most_15_on_3yr_avg_eps",
            Outcome.NEEDS_STAGE_1B,
            "P/E on 3-yr average EPS is a Stage 1b own-history test (plan.md §13); "
            f"trailing pe_ratio={pe} is reported for context only",
            (),
        )
    )

    pb = record.get_float("price_to_book")
    criteria.append(
        Criterion(
            "pb_at_most_1_5",
            Outcome.PASS if pb is not None and pb <= 1.5 else (Outcome.FAIL if pb is not None else Outcome.NEEDS_STAGE_1B),
            f"P/B={pb}" if pb is not None else "price_to_book missing",
            ("price_to_book",),
        )
    )

    if pe is not None and pb is not None:
        graham_number = pe * pb
        gn_outcome = Outcome.PASS if graham_number <= 22.5 else Outcome.FAIL
        gn_detail = f"P/E x P/B = {graham_number:.2f}"
    else:
        gn_outcome = Outcome.NEEDS_STAGE_1B
        gn_detail = "pe_ratio or price_to_book missing"
    criteria.append(Criterion("graham_number_at_most_22_5", gn_outcome, gn_detail, ("pe_ratio", "price_to_book")))

    criteria.append(
        Criterion(
            "dividend_record_at_least_10y",
            Outcome.NEEDS_STAGE_1B,
            "dividend-record history test — plan.md §13 assigns this to Stage 1b",
            (),
        )
    )

    outcome = overall_outcome(tuple(criteria))
    return ScreenResult("Graham Defensive Criteria", "A", outcome, tuple(criteria))


def run_track_a_stage1(record: CompanyRecord) -> dict[str, ScreenResult]:
    """Run every Track A Stage 1a screen for one company.

    Returns a dict keyed by screen name so callers (the pipeline, tests,
    the dossier) can inspect each attributed screen individually. Stage 1
    clearance for Track A is `quality_gate` AND `growth_gate` passing —
    the other two are refinements/attribution only (see their docstrings).
    """
    return {
        "quality_gate": quality_gate(record),
        "growth_gate": growth_gate(record),
        "moat_quality_refinement": moat_quality_refinement(record),
        "graham_defensive_criteria": graham_defensive_criteria(record),
    }


def clears_track_a_stage1(results: dict[str, ScreenResult]) -> bool:
    """The two mandatory QGLP gates must both PASS; refinements are informational."""
    return (
        results["quality_gate"].outcome == Outcome.PASS
        and results["growth_gate"].outcome == Outcome.PASS
    )
