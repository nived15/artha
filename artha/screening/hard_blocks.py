"""Stage 2 — fatal-flaw hard blocks (plan.md §5.4).

"Any 'no' or 'unknown' ends the analysis. No score, no override." This
module implements the automatable fatal-flaw questions plus the two named
hard gates (Greenblatt ranking, Pabrai asymmetry). Questions plan.md itself
marks as requiring LLM-verified filings (business explainability, single-
customer dependency, price-assumption plausibility) are reported as
NEEDS_STAGE_3, never assumed to pass.

Promoter pledging note: plan.md §13.3a assumed no affordable API exposes
pledging as a structured field, so it specifies LLM-verification with
fail-closed semantics. Phase 1's §13.4 desk research found `Pledged
percentage` *is* a native, exportable Screener field — so this module
automates it from Stage 1a data, still failing closed if the field is
missing (the plan's fail-closed spirit, now on better data).
"""

from __future__ import annotations

from dataclasses import dataclass

from artha.screening.models import Criterion, CompanyRecord, Outcome, ScreenResult, overall_outcome

# plan.md §5.4: "pledge > 20% of promoter holding" (Agrawal) is a red flag.
PLEDGE_RED_FLAG_PCT = 20.0


def promoter_pledging_check(record: CompanyRecord) -> Criterion:
    """Fails closed: an unknown pledge % ends the analysis, per plan.md §13.3a."""
    pledge = record.get_float("promoter_pledge_pct")
    if pledge is None:
        return Criterion(
            "promoter_pledging",
            Outcome.FAIL,
            "promoter_pledge_pct unknown — fails closed per plan.md §13.3a",
            ("promoter_pledge_pct",),
        )
    passed = pledge <= PLEDGE_RED_FLAG_PCT
    return Criterion(
        "promoter_pledging",
        Outcome.PASS if passed else Outcome.FAIL,
        f"promoter_pledge_pct={pledge} (red-flag threshold: >{PLEDGE_RED_FLAG_PCT}%)",
        ("promoter_pledge_pct",),
    )


def promoter_integrity_red_flags(record: CompanyRecord) -> ScreenResult:
    """Expanded promoter-integrity red flags (plan.md §5.4): declining
    promoter holding over 3 years; pledge > 20%; SEBI show-cause/adverse
    RPT/auditor resignation (Fisher Point 15) — the last three are
    qualitative filing-review items, deferred to Stage 3.
    """
    criteria: list[Criterion] = [promoter_pledging_check(record)]

    trend = record.get_float("promoter_holding_trend_3y")
    if trend is None:
        criteria.append(Criterion("promoter_holding_not_declining", Outcome.NEEDS_STAGE_1B, "promoter_holding_trend_3y missing", ("promoter_holding_trend_3y",)))
    else:
        criteria.append(
            Criterion(
                "promoter_holding_not_declining",
                Outcome.PASS if trend >= 0 else Outcome.FAIL,
                f"3yr promoter holding trend={trend}",
                ("promoter_holding_trend_3y",),
            )
        )

    criteria.append(
        Criterion(
            "no_sebi_rpt_auditor_flags",
            Outcome.NEEDS_STAGE_3,
            "SEBI show-cause / adverse RPT / auditor resignation (Fisher Point 15) — filing-review item",
            (),
        )
    )

    outcome = overall_outcome(tuple(criteria))
    return ScreenResult("Promoter Integrity Red Flags", "both", outcome, tuple(criteria))


def fatal_flaw_checklist(record: CompanyRecord) -> ScreenResult:
    """The ~15 disqualifying questions (plan.md §5.4). Only the questions
    answerable from Stage 1a data are automated here; the rest are
    reported NEEDS_STAGE_3, matching the plan's own routing of
    unanswerable questions to mandatory LLM-verified Stage 3 items.
    """
    criteria: list[Criterion] = [promoter_pledging_check(record)]

    ocf_pat = record.get_float("ocf_to_pat")
    if ocf_pat is None:
        criteria.append(Criterion("profit_becomes_cash", Outcome.NEEDS_STAGE_1B, "ocf_to_pat missing — chronic divergence needs multi-year history", ("ocf_to_pat",)))
    else:
        # A single-year ratio is only a proxy for "chronic" divergence —
        # the true chronic test is a Stage 1b multi-year comparison.
        criteria.append(
            Criterion(
                "profit_becomes_cash",
                Outcome.PASS if ocf_pat >= 0.8 else Outcome.FAIL,
                f"ocf_to_pat={ocf_pat} (single-year proxy; chronic divergence is a Stage 1b test)",
                ("ocf_to_pat",),
            )
        )

    for name, detail in (
        ("survives_worst_year_without_dilution", "bear-case stress scenario — qualitative Stage 3 judgment"),
        ("no_single_point_of_failure_dependency", "single customer/regulator/input concentration — filing-review item"),
        ("business_explainable_in_five_sentences", "circle-of-competence test — Stage 3 understandability gate (plan.md §5.5)"),
        ("price_assumption_plausible", "what the price already assumes — qualitative Stage 3 judgment"),
        ("no_serial_equity_dilution", "share-count history — Stage 1b own-history test"),
    ):
        criteria.append(Criterion(name, Outcome.NEEDS_STAGE_3, detail, ()))

    outcome = overall_outcome(tuple(criteria))
    return ScreenResult("Fatal-Flaw Checklist", "both", outcome, tuple(criteria))


# --- Greenblatt Magic Formula ranking gate (plan.md §5.4) -----------------

_LENDING_PROFILE = "profile_2_banking"
_INSURANCE_PROFILE = "profile_3_insurance"
_STANDARD_PROFILE = "profile_1_standard"


@dataclass(frozen=True)
class GreenblattInputs:
    ticker: str
    arithmetic_profile: str
    roc_or_substitute: float | None   # ROC (Profile 1) or sector-native return substitute (Profile 2-5)
    earnings_yield: float | None      # EBIT/EV (Profile 1) or PAT/MarketCap substitute (Profile 2-5)


@dataclass(frozen=True)
class GreenblattRankResult:
    ticker: str
    roc_rank: int
    earnings_yield_rank: int
    combined_rank: int
    percentile: float  # 0-100, lower is better
    passed: bool  # in the best decile


def company_to_greenblatt_inputs(record: CompanyRecord) -> GreenblattInputs:
    """Compute the ROC/EY inputs for one company, per plan.md §5.4's
    substitution rule: Profile 1 uses EBIT-based ROC/EV; Profile 2-5 use a
    sector-native return and PAT/MarketCap earnings yield instead, flagged
    in the dossier (§6.21) as Artha's extension, not Greenblatt's method.
    """
    if record.arithmetic_profile == _STANDARD_PROFILE:
        ebit = record.get_float("ebit")
        nwc = record.get_float("net_working_capital_ex_cash_ex_debt")
        nfa = record.get_float("net_fixed_assets_ex_goodwill")
        ev = record.get_float("enterprise_value")
        roc = ebit / (nwc + nfa) if ebit is not None and nwc is not None and nfa is not None and (nwc + nfa) != 0 else None
        ey = ebit / ev if ebit is not None and ev is not None and ev != 0 else None
        return GreenblattInputs(record.ticker, record.arithmetic_profile, roc, ey)

    if record.arithmetic_profile in (_LENDING_PROFILE, _INSURANCE_PROFILE):
        # Greenblatt explicitly excludes financials/utilities — the plan's
        # substitute is a sector-native return (ROA for lending) and
        # PAT/MarketCap earnings yield. Not yet wired to Stage 1a fields
        # (Profile 2/3 fields are themselves Stage 1b per docs/phase1_validation_spike.md).
        return GreenblattInputs(record.ticker, record.arithmetic_profile, None, None)

    return GreenblattInputs(record.ticker, record.arithmetic_profile, None, None)


def rank_by_greenblatt(records: list[CompanyRecord], *, best_decile_pct: float = 10.0) -> dict[str, GreenblattRankResult]:
    """Rank a screened universe by Greenblatt's combined ordinal rank.

    Companies with unresolvable ROC/EY (e.g. Profile 2-5 names pending
    their substitute fields) are excluded from ranking, not scored zero —
    an absent input is not evidence of a bad company.
    """
    inputs = [company_to_greenblatt_inputs(r) for r in records]
    rankable = [i for i in inputs if i.roc_or_substitute is not None and i.earnings_yield is not None]

    if not rankable:
        return {}

    by_roc = sorted(rankable, key=lambda i: i.roc_or_substitute, reverse=True)
    roc_rank = {i.ticker: rank + 1 for rank, i in enumerate(by_roc)}

    by_ey = sorted(rankable, key=lambda i: i.earnings_yield, reverse=True)
    ey_rank = {i.ticker: rank + 1 for rank, i in enumerate(by_ey)}

    combined = {i.ticker: roc_rank[i.ticker] + ey_rank[i.ticker] for i in rankable}
    n = len(rankable)
    ordered = sorted(combined.items(), key=lambda kv: kv[1])

    results: dict[str, GreenblattRankResult] = {}
    for position, (ticker, combined_rank) in enumerate(ordered, start=1):
        percentile = position / n * 100.0
        results[ticker] = GreenblattRankResult(
            ticker=ticker,
            roc_rank=roc_rank[ticker],
            earnings_yield_rank=ey_rank[ticker],
            combined_rank=combined_rank,
            percentile=percentile,
            passed=percentile <= best_decile_pct,
        )
    return results


# --- Pabrai asymmetry gate (plan.md §5.4) ---------------------------------


@dataclass(frozen=True)
class DownsideFloorScore:
    """The Downside-Floor Score, /16. plan.md §5.4 names four test
    categories; each is scored 0-4 here (implying two Pabrai sub-tests per
    category, per the plan's "8 tests, /16" — the itemized 8-test rubric
    is not transcribed beyond these four category names, so each category
    covers two of the eight)."""

    net_cash_or_tangible_asset_backing: int  # 0-4
    bear_case_fcf_survival: int              # 0-4
    debt_safety: int                         # 0-4
    liquidation_value_coverage: int          # 0-4

    def __post_init__(self) -> None:
        for name, value in (
            ("net_cash_or_tangible_asset_backing", self.net_cash_or_tangible_asset_backing),
            ("bear_case_fcf_survival", self.bear_case_fcf_survival),
            ("debt_safety", self.debt_safety),
            ("liquidation_value_coverage", self.liquidation_value_coverage),
        ):
            if not 0 <= value <= 4:
                raise ValueError(f"{name} must be in [0, 4], got {value}")

    @property
    def total(self) -> int:
        return (
            self.net_cash_or_tangible_asset_backing
            + self.bear_case_fcf_survival
            + self.debt_safety
            + self.liquidation_value_coverage
        )


@dataclass(frozen=True)
class PabraiGateResult:
    downside_floor_score: int  # /16
    downside_floor_passed: bool
    asymmetry_ratio: float
    asymmetry_passed: bool
    passed: bool  # both tests must pass — fails either, hard disqualify, no override


def pabrai_asymmetry_gate(
    downside_floor: DownsideFloorScore,
    *,
    bull_case_upside_pct: float,
    bear_case_downside_pct: float,
) -> PabraiGateResult:
    """plan.md §5.4: Downside-Floor Score >= 10/16 AND Asymmetry Ratio
    (bull-case upside % / bear-case downside %) >= 3:1. Fails either ->
    hard disqualify, no override.
    """
    if bear_case_downside_pct <= 0:
        raise ValueError("bear_case_downside_pct must be positive (it is a downside magnitude)")

    floor_score = downside_floor.total
    floor_passed = floor_score >= 10
    ratio = bull_case_upside_pct / bear_case_downside_pct
    ratio_passed = ratio >= 3.0

    return PabraiGateResult(
        downside_floor_score=floor_score,
        downside_floor_passed=floor_passed,
        asymmetry_ratio=ratio,
        asymmetry_passed=ratio_passed,
        passed=floor_passed and ratio_passed,
    )
