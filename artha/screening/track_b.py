"""Track B (asymmetric bets) Stage 1a screens — plan.md §5.3.

Only Lynch PEG and Kedia SMILE are meaningfully Stage-1a-computable from a
single snapshot row. Davis Double Play's entry condition ("P/E in the
bottom tercile of the stock's own 5-year history") is explicitly a Stage
1b own-history test per plan.md §13 — this module implements the
Double Play's *implied-return formula* as a pure calculator (callers
supply the Stage 1b percentile once it exists) and screens the
Stage-1a-available "reported acceleration" half of the test. O'Neil
CANSLIM's momentum overlay needs live price/volume/RS-rating data this
codebase does not yet ingest (no market-data provider is built before
Phase 6) — its scoring function is implemented so it is ready to wire up,
but is not run by default.
"""

from __future__ import annotations

from typing import Any

from artha.screening.models import Criterion, Outcome, ScreenResult, CompanyRecord, overall_outcome


def lynch_peg(record: CompanyRecord) -> ScreenResult:
    """PEG = P/E / trailing 5yr EPS growth% (dividend-yield-adjusted for
    stalwarts/slow growers). Buy zone PEG < 1.0 (primary band 0.5-1.0)."""
    criteria: list[Criterion] = []

    pe = record.get_float("pe_ratio")
    growth = record.get_float("profit_growth_5y")  # proxy for trailing EPS growth %
    dividend_yield = record.get_float("dividend_yield_pct") or 0.0

    if pe is None or growth is None:
        criteria.append(
            Criterion(
                "peg_computable",
                Outcome.NEEDS_STAGE_1B,
                f"pe_ratio={pe}, profit_growth_5y={growth} — cannot compute PEG",
                ("pe_ratio", "profit_growth_5y"),
            )
        )
        return ScreenResult("Lynch PEG Screen", "B", Outcome.NEEDS_STAGE_1B, tuple(criteria))

    # Lynch's taxonomy determines whether the dividend-yield adjustment applies.
    category = _lynch_category(growth)
    if category in ("stalwart", "slow_grower"):
        denominator = growth + dividend_yield
        peg_detail = f"PEG = {pe} / ({growth} + {dividend_yield} div yield)"
    else:
        denominator = growth
        peg_detail = f"PEG = {pe} / {growth}"

    if denominator <= 0:
        criteria.append(Criterion("peg_computable", Outcome.FAIL, f"non-positive growth denominator ({denominator})", ("profit_growth_5y",)))
        return ScreenResult("Lynch PEG Screen", "B", Outcome.FAIL, tuple(criteria))

    peg = pe / denominator
    in_buy_zone = peg < 1.0
    criteria.append(
        Criterion(
            "peg_under_1_0",
            Outcome.PASS if in_buy_zone else Outcome.FAIL,
            f"{peg_detail} = {peg:.2f} ({'in buy zone' if in_buy_zone else 'outside buy zone'}; "
            f"primary band 0.5-1.0)",
            ("pe_ratio", "profit_growth_5y", "dividend_yield_pct"),
        )
    )
    criteria.append(
        Criterion(
            "lynch_category",
            Outcome.PASS,
            f"category={category} (5yr EPS growth={growth}%)",
            ("profit_growth_5y",),
        )
    )

    outcome = overall_outcome(tuple(criteria), mandatory=("peg_under_1_0",))
    result = ScreenResult("Lynch PEG Screen", "B", outcome, tuple(criteria), score=peg, score_max=1.0)
    return result


def _lynch_category(eps_growth_5y: float) -> str:
    """Lynch's taxonomy — fast grower / stalwart / slow grower, by 5yr EPS CAGR.
    Cyclical/turnaround/asset-play require qualitative judgment (Stage 3),
    so this classifier only distinguishes by growth rate.
    """
    if eps_growth_5y >= 20:
        return "fast_grower"
    if eps_growth_5y >= 8:
        return "stalwart"
    if eps_growth_5y <= 6:
        return "slow_grower"
    return "stalwart"  # the 6-8% gap between bands defaults to the nearer, less extreme label


def davis_double_play_implied_return(entry_pe: float, sector_median_pe: float, trailing_eps_cagr_pct: float) -> float:
    """The Double Play's multiplicative implied-return score (plan.md §5.3):

        (1 + trailing EPS CAGR)^3 x (sector-median P/E / entry P/E) - 1

    A pure calculator — the caller supplies entry P/E, sector-median P/E
    (an aggregate over the screened universe, not a single-company field)
    and trailing EPS CAGR. Never additive, per the plan's explicit note.
    """
    if entry_pe <= 0:
        raise ValueError("entry_pe must be positive")
    growth_component = (1 + trailing_eps_cagr_pct / 100.0) ** 3
    rerating_component = sector_median_pe / entry_pe
    return growth_component * rerating_component - 1


def davis_double_play(
    record: CompanyRecord,
    *,
    entry_pe_percentile_5y: float | None = None,
    sector_median_pe: float | None = None,
) -> ScreenResult:
    """Davis Double Play screen.

    `entry_pe_percentile_5y` (0-100, own 5-year P/E history) and
    `sector_median_pe` are Stage 1b/aggregate inputs this module cannot
    compute from a single Stage 1a row — pass them once a Stage 1b lookup
    or sector-median computation exists; until then this reports
    NEEDS_STAGE_1B for the percentile leg while still screening the
    Stage-1a-available reported-acceleration and quality legs.
    """
    criteria: list[Criterion] = []

    if entry_pe_percentile_5y is None:
        criteria.append(
            Criterion(
                "entry_pe_bottom_tercile_5y",
                Outcome.NEEDS_STAGE_1B,
                "own 5-year P/E percentile — Stage 1b lookup, not yet supplied",
                (),
            )
        )
    else:
        in_tercile = entry_pe_percentile_5y <= 33.3
        criteria.append(
            Criterion(
                "entry_pe_bottom_tercile_5y",
                Outcome.PASS if in_tercile else Outcome.FAIL,
                f"entry P/E percentile of own 5yr history = {entry_pe_percentile_5y}",
                ("pe_ratio",),
            )
        )

    pe = record.get_float("pe_ratio")
    if pe is not None and sector_median_pe is not None:
        below_sector = pe <= 0.8 * sector_median_pe
        criteria.append(
            Criterion(
                "entry_pe_at_most_80pct_sector_median",
                Outcome.PASS if below_sector else Outcome.FAIL,
                f"entry P/E={pe}, sector-median P/E={sector_median_pe} (80% threshold={0.8 * sector_median_pe:.2f})",
                ("pe_ratio",),
            )
        )
    else:
        criteria.append(
            Criterion(
                "entry_pe_at_most_80pct_sector_median",
                Outcome.NEEDS_STAGE_1B,
                "sector-median P/E not supplied (aggregate over the screened universe)",
                (),
            )
        )

    trailing_growth = record.get_float("profit_growth_5y")
    criteria.append(
        Criterion(
            "trailing_eps_growth_at_least_15",
            Outcome.PASS if trailing_growth is not None and trailing_growth >= 15 else (Outcome.FAIL if trailing_growth is not None else Outcome.NEEDS_STAGE_1B),
            f"trailing 5yr growth={trailing_growth}" if trailing_growth is not None else "profit_growth_5y missing",
            ("profit_growth_5y",),
        )
    )

    latest_q = record.get_float("eps_growth_latest_q_yoy")
    ttm = record.get_float("eps_growth_ttm_yoy")
    if latest_q is not None and ttm is not None:
        accelerating = latest_q > 0 and ttm > 0
        criteria.append(
            Criterion(
                "reported_acceleration",
                Outcome.PASS if accelerating else Outcome.FAIL,
                f"latest-quarter YoY={latest_q}, TTM vs prior TTM={ttm} (both must be positive)",
                ("eps_growth_latest_q_yoy", "eps_growth_ttm_yoy"),
            )
        )
    else:
        criteria.append(
            Criterion(
                "reported_acceleration",
                Outcome.NEEDS_STAGE_1B,
                "eps_growth_latest_q_yoy / eps_growth_ttm_yoy missing",
                ("eps_growth_latest_q_yoy", "eps_growth_ttm_yoy"),
            )
        )

    roe = record.get_float("roe")
    criteria.append(
        Criterion(
            "roe_at_least_15",
            Outcome.PASS if roe is not None and roe >= 15 else (Outcome.FAIL if roe is not None else Outcome.NEEDS_STAGE_1B),
            f"ROE={roe}" if roe is not None else "roe missing",
            ("roe",),
        )
    )

    de = record.get_float("debt_to_equity")
    criteria.append(
        Criterion(
            "debt_to_equity_at_most_1_5",
            Outcome.PASS if de is not None and de <= 1.5 else (Outcome.FAIL if de is not None else Outcome.NEEDS_STAGE_1B),
            f"D/E={de}" if de is not None else "debt_to_equity missing",
            ("debt_to_equity",),
        )
    )

    if pe is not None:
        criteria.append(
            Criterion(
                "pe_floor_at_least_5",
                Outcome.PASS if pe >= 5 else Outcome.FAIL,
                f"P/E={pe} (floor excludes distress/value-traps)",
                ("pe_ratio",),
            )
        )
    else:
        criteria.append(Criterion("pe_floor_at_least_5", Outcome.NEEDS_STAGE_1B, "pe_ratio missing", ("pe_ratio",)))

    outcome = overall_outcome(tuple(criteria))
    return ScreenResult("Davis Double Play Screen", "B", outcome, tuple(criteria))


def kedia_smile(record: CompanyRecord, *, liquidity_floor_cr: float = 200.0, ceiling_cr: float = 5000.0) -> ScreenResult:
    """Kedia SMILE screen — market cap band, incorporation years, promoter
    holding, low analyst coverage. "Large aspiration"/"Extra-large market
    opportunity" (the L and E letters) are qualitative and deferred to
    Stage 3, per plan.md §5.3.
    """
    criteria: list[Criterion] = []

    mcap = record.get_float("market_cap")
    if mcap is not None:
        in_band = liquidity_floor_cr <= mcap <= ceiling_cr
        criteria.append(
            Criterion(
                "market_cap_in_smile_band",
                Outcome.PASS if in_band else Outcome.FAIL,
                f"market_cap={mcap} Cr (band: {liquidity_floor_cr}-{ceiling_cr} Cr)",
                ("market_cap",),
            )
        )
    else:
        criteria.append(Criterion("market_cap_in_smile_band", Outcome.NEEDS_STAGE_1B, "market_cap missing", ("market_cap",)))

    years = record.get_float("years_since_incorporation")
    if years is not None:
        in_band = 10 <= years <= 35
        criteria.append(
            Criterion(
                "incorporation_years_10_to_35",
                Outcome.PASS if in_band else Outcome.FAIL,
                f"years_since_incorporation={years}",
                ("years_since_incorporation",),
            )
        )
    else:
        criteria.append(Criterion("incorporation_years_10_to_35", Outcome.NEEDS_STAGE_1B, "years_since_incorporation missing", ("years_since_incorporation",)))

    promoter = record.get_float("promoter_holding_pct")
    criteria.append(
        Criterion(
            "promoter_holding_at_least_40",
            Outcome.PASS if promoter is not None and promoter >= 40 else (Outcome.FAIL if promoter is not None else Outcome.NEEDS_STAGE_1B),
            f"promoter_holding_pct={promoter}" if promoter is not None else "promoter_holding_pct missing",
            ("promoter_holding_pct",),
        )
    )

    coverage = record.get_float("analyst_coverage_count")
    if coverage is not None:
        criteria.append(
            Criterion(
                "low_analyst_coverage",
                Outcome.PASS if coverage <= 2 else Outcome.FAIL,
                f"analyst_coverage_count={coverage}",
                ("analyst_coverage_count",),
            )
        )
    else:
        criteria.append(Criterion("low_analyst_coverage", Outcome.NEEDS_STAGE_1B, "analyst_coverage_count missing", ("analyst_coverage_count",)))

    criteria.append(
        Criterion(
            "large_aspiration_and_tam",
            Outcome.NEEDS_STAGE_3,
            "qualitative — Kedia's 'L' and 'E' letters, deferred to Stage 3 per plan.md §5.3",
            (),
        )
    )

    # Stage 1a mandatory legs only; the qualitative L/E letters are
    # informational at this stage (Stage 3 resolves them).
    mandatory = ("market_cap_in_smile_band", "incorporation_years_10_to_35", "promoter_holding_at_least_40", "low_analyst_coverage")
    outcome = overall_outcome(tuple(criteria), mandatory=mandatory)
    return ScreenResult("Kedia SMILE Screen", "B", outcome, tuple(criteria))


def canslim_overlay(
    record: CompanyRecord,
    *,
    price_within_5pct_of_pivot: bool | None = None,
    breakout_volume_ratio: float | None = None,
    relative_strength_percentile: float | None = None,
    market_in_uptrend: bool | None = None,
) -> ScreenResult:
    """O'Neil CANSLIM momentum overlay — Track B only, applied *after* the
    fundamental screens above pass (plan.md §5.3). Needs live price/volume/
    breadth data no provider in this codebase ingests yet (Phase 5/6
    territory) — every technical input defaults to NEEDS_STAGE_3 until a
    market-data feed is wired up. This function is ready to accept that
    feed's output without further design change.
    """
    criteria: list[Criterion] = []

    current_q_growth = record.get_float("eps_growth_latest_q_yoy")
    criteria.append(
        Criterion(
            "current_quarter_eps_growth_at_least_25",
            Outcome.PASS if current_q_growth is not None and current_q_growth >= 25 else (Outcome.FAIL if current_q_growth is not None else Outcome.NEEDS_STAGE_1B),
            f"current-quarter EPS YoY={current_q_growth}" if current_q_growth is not None else "eps_growth_latest_q_yoy missing",
            ("eps_growth_latest_q_yoy",),
        )
    )

    eps_cagr_3y = record.get_float("profit_growth_3y")
    roe = record.get_float("roe")
    if eps_cagr_3y is not None and roe is not None:
        ok = eps_cagr_3y >= 25 and roe >= 17
        criteria.append(
            Criterion(
                "eps_cagr_3y_25_and_roe_17",
                Outcome.PASS if ok else Outcome.FAIL,
                f"3yr EPS CAGR={eps_cagr_3y}, ROE={roe}",
                ("profit_growth_3y", "roe"),
            )
        )
    else:
        criteria.append(Criterion("eps_cagr_3y_25_and_roe_17", Outcome.NEEDS_STAGE_1B, "profit_growth_3y or roe missing", ("profit_growth_3y", "roe")))

    def _from_technical(name: str, value: Any, detail: str) -> Criterion:
        if value is None:
            return Criterion(name, Outcome.NEEDS_STAGE_3, f"{detail} — no market-data feed wired up yet", ())
        return Criterion(name, Outcome.PASS if value else Outcome.FAIL, detail, ())

    criteria.append(_from_technical("price_within_5pct_of_pivot", price_within_5pct_of_pivot, "chart-base breakout pivot proximity"))
    criteria.append(
        Criterion(
            "breakout_volume_at_least_40pct_above_avg",
            Outcome.NEEDS_STAGE_3 if breakout_volume_ratio is None else (Outcome.PASS if breakout_volume_ratio >= 1.4 else Outcome.FAIL),
            f"breakout_volume_ratio={breakout_volume_ratio}" if breakout_volume_ratio is not None else "no market-data feed wired up yet",
            (),
        )
    )
    criteria.append(
        Criterion(
            "relative_strength_at_least_80th_percentile",
            Outcome.NEEDS_STAGE_3 if relative_strength_percentile is None else (Outcome.PASS if relative_strength_percentile >= 80 else Outcome.FAIL),
            f"RS percentile={relative_strength_percentile}" if relative_strength_percentile is not None else "no market-data feed wired up yet",
            (),
        )
    )
    criteria.append(_from_technical("market_in_confirmed_uptrend", market_in_uptrend, "Nifty 50/Sensex market-direction assessment"))

    outcome = overall_outcome(tuple(criteria))
    return ScreenResult("CANSLIM Momentum Overlay", "B", outcome, tuple(criteria))


def run_track_b_stage1(
    record: CompanyRecord,
    *,
    entry_pe_percentile_5y: float | None = None,
    sector_median_pe: float | None = None,
) -> dict[str, ScreenResult]:
    """Run every Track B Stage 1a screen for one company (fundamentals only —
    CANSLIM is a separate, opt-in overlay run after these pass, per plan.md §5.3).
    """
    return {
        "lynch_peg": lynch_peg(record),
        "davis_double_play": davis_double_play(
            record, entry_pe_percentile_5y=entry_pe_percentile_5y, sector_median_pe=sector_median_pe
        ),
        "kedia_smile": kedia_smile(record),
    }


def clears_track_b_stage1(results: dict[str, ScreenResult]) -> bool:
    """Track B clears Stage 1 if it qualifies under *any* of the three named
    screens — they are alternative theses (a Davis re-rating, a Lynch PEG
    bargain, a Kedia SMILE small-cap), not a conjunction plan.md requires
    a name to satisfy simultaneously.
    """
    return any(r.outcome == Outcome.PASS for r in results.values())
