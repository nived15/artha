"""The per-track scorecard (plan.md §9, §11 Phase 4).

"Time-weighted returns for skill, money-weighted for wealth, both post-tax
including accrued liability on unrealised gains. Judged against each
benchmark independently — beating one and losing the other is a loss."

This module computes both return measures and compares them against the
frozen benchmark's two components (config/ips.md §3), independently, per
track. plan.md §11's Phase 4 exit criterion is that this reconciles against
a hand-computed example — see tests/test_scorecard.py.

**Sign conventions (the classic source of bugs here, so stated explicitly):**
- `CashFlow` (used by `xirr`) is from the *investor's own cash* perspective:
  a BUY is a negative cashflow (cash leaves your pocket), a SELL is
  positive (cash returns to it), and the final holding is one last
  positive cashflow at the valuation date (as if liquidated).
- `TwrPoint.cashflow` (used by `time_weighted_return`) is from the
  *portfolio's asset base* perspective: a BUY is a positive contribution
  to the portfolio being measured, a SELL is a negative withdrawal from it.

**Simplification carried forward honestly:** this ledger has no live price
feed, so `time_weighted_return` requires the caller to supply periodic
valuation marks (e.g. from a Screener snapshot's `price` field, or a manual
mark) — it cannot derive them from trades alone. And `track_scorecard`'s
post-tax XIRR applies each fiscal year's realized capital-gains tax as one
lump-sum outflow at the `as_of_date` rather than modeling the exact ITR
payment date — a reasonable approximation for a paper ledger's own record,
not a proper tax-planning tool.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from artha.ledger.positions import Position, list_open_positions
from artha.ledger.tax import LTCG_ANNUAL_EXEMPTION, accrued_tax_on_unrealized, capital_gains_tax, fiscal_year_label
from artha.ledger.tax_lots import classify_gain, holding_days, list_realized_gains


@dataclass(frozen=True)
class CashFlow:
    date: str      # ISO date
    amount: float  # investor-cash convention: outflow negative, inflow positive


@dataclass(frozen=True)
class TwrPoint:
    date: str                     # ISO date
    value_before_cashflow: float  # portfolio market value immediately before this date's cashflow
    cashflow: float = 0.0          # portfolio-contribution convention: BUY positive, SELL negative


def _days_from(t0: date, d: str) -> float:
    return (date.fromisoformat(d) - t0).days


def xirr(cashflows: list[CashFlow], *, tolerance: float = 1e-6, max_iterations: int = 100) -> float:
    """Money-weighted annualized return via Newton-Raphson with a bisection fallback.

    Requires at least one negative and one non-negative cashflow (otherwise
    there is no rate that zeroes the NPV). Raises ValueError if it cannot
    find one.
    """
    if len(cashflows) < 2:
        raise ValueError("xirr needs at least two cashflows")
    ordered = sorted(cashflows, key=lambda c: c.date)
    t0 = date.fromisoformat(ordered[0].date)
    if not any(c.amount < 0 for c in ordered) or not any(c.amount > 0 for c in ordered):
        raise ValueError("xirr needs at least one negative and one positive cashflow")

    def npv(rate: float) -> float:
        return sum(c.amount / (1.0 + rate) ** (_days_from(t0, c.date) / 365.0) for c in ordered)

    def dnpv(rate: float) -> float:
        total = 0.0
        for c in ordered:
            days = _days_from(t0, c.date)
            if days == 0:
                continue
            total += -(days / 365.0) * c.amount / (1.0 + rate) ** (days / 365.0 + 1.0)
        return total

    rate = 0.1
    for _ in range(max_iterations):
        f = npv(rate)
        if abs(f) < tolerance:
            return rate
        d = dnpv(rate)
        if d == 0:
            break
        next_rate = rate - f / d
        if next_rate <= -0.999999:
            next_rate = (rate - 0.999999) / 2.0
        rate = next_rate

    # Newton-Raphson didn't converge (e.g. a pathological cashflow shape) —
    # fall back to bisection over a wide, sane rate range.
    lo, hi = -0.999999, 100.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        raise ValueError("xirr did not converge — check cashflow signs/amounts")
    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < tolerance:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


def time_weighted_return(points: list[TwrPoint]) -> float:
    """True time-weighted return, chained across subperiods split at each cashflow.

    `points` must be chronologically ordered. The first point's cashflow is
    the initial contribution (value_before_cashflow=0). Each subperiod
    return is (next.value_before_cashflow) / (this.value_before_cashflow +
    this.cashflow) - 1; periods with zero capital at risk are skipped
    (contribute a 0% subperiod, not a divide-by-zero).
    """
    if len(points) < 2:
        raise ValueError("time_weighted_return needs at least two points")
    ordered = sorted(points, key=lambda p: p.date)
    cumulative = 1.0
    for i in range(len(ordered) - 1):
        start_value = ordered[i].value_before_cashflow + ordered[i].cashflow
        end_value = ordered[i + 1].value_before_cashflow
        if start_value == 0:
            continue
        cumulative *= 1.0 + (end_value / start_value - 1.0)
    return cumulative - 1.0


def annualize(total_return: float, days: int) -> float:
    """Convert a total return over `days` into a CAGR. days<=0 returns the raw total_return."""
    if days <= 0:
        return total_return
    return (1.0 + total_return) ** (365.0 / days) - 1.0


def record_benchmark_nav(conn: sqlite3.Connection, *, fund_name: str, nav_date: str, nav: float) -> None:
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO benchmark_nav (fund_name, nav_date, nav) VALUES (?, ?, ?)",
            (fund_name, nav_date, nav),
        )


def get_benchmark_nav_series(conn: sqlite3.Connection, fund_name: str) -> list[tuple[str, float]]:
    rows = conn.execute(
        "SELECT nav_date, nav FROM benchmark_nav WHERE fund_name = ? ORDER BY nav_date ASC",
        (fund_name,),
    ).fetchall()
    return [(r["nav_date"], r["nav"]) for r in rows]


def fund_total_return(nav_series: list[tuple[str, float]]) -> float:
    """Simple total return of a no-cashflow NAV series: nav_end/nav_start - 1."""
    if len(nav_series) < 2:
        raise ValueError("fund_total_return needs at least two NAV points")
    ordered = sorted(nav_series, key=lambda p: p[0])
    return ordered[-1][1] / ordered[0][1] - 1.0


def fund_annualized_return(nav_series: list[tuple[str, float]]) -> float:
    ordered = sorted(nav_series, key=lambda p: p[0])
    days = _days_from(date.fromisoformat(ordered[0][0]), ordered[-1][0])
    return annualize(fund_total_return(nav_series), int(days))


@dataclass(frozen=True)
class BenchmarkComparison:
    sleeve_return: float
    index_return: float
    factor_return: float
    beats_index: bool
    beats_factor: bool

    @property
    def beats_benchmark_set(self) -> bool:
        """config/ips.md §3: "Beating one component while trailing the other
        will not count as beating the frozen benchmark set.\""""
        return self.beats_index and self.beats_factor


def compare_to_benchmark(sleeve_return: float, index_return: float, factor_return: float) -> BenchmarkComparison:
    return BenchmarkComparison(
        sleeve_return=sleeve_return,
        index_return=index_return,
        factor_return=factor_return,
        beats_index=sleeve_return > index_return,
        beats_factor=sleeve_return > factor_return,
    )


@dataclass(frozen=True)
class TrackScorecard:
    track: str
    as_of_date: str
    invested_capital: float           # sum of BUY cash outlay to date
    realized_tax: float               # capital-gains tax owed on realized gains to date
    accrued_tax_on_unrealized: float  # estimated tax if all open positions sold today
    gross_ending_value: float         # open positions' market value, pre-tax
    post_tax_ending_value: float      # gross_ending_value - accrued_tax_on_unrealized
    xirr_gross: float
    xirr_post_tax: float


def _trade_cashflows(conn: sqlite3.Connection, track: str) -> list[CashFlow]:
    rows = conn.execute(
        "SELECT side, quantity, price, trade_date FROM trades WHERE track = ? ORDER BY trade_date ASC",
        (track,),
    ).fetchall()
    cashflows = []
    for r in rows:
        amount = r["quantity"] * r["price"]
        cashflows.append(CashFlow(date=r["trade_date"], amount=-amount if r["side"] == "BUY" else amount))
    return cashflows


def track_scorecard(
    conn: sqlite3.Connection,
    *,
    track: str,
    as_of_date: str,
    current_prices: dict[str, float],
) -> TrackScorecard:
    """Assemble one track's post-tax money-weighted scorecard as of a given date.

    `current_prices` maps ticker -> current mark used to value open
    positions (e.g. from the latest Screener snapshot's `price` field).
    """
    trade_cashflows = _trade_cashflows(conn, track)
    invested_capital = -sum(cf.amount for cf in trade_cashflows if cf.amount < 0)

    realized = list_realized_gains(conn, track=track)
    by_fiscal_year: dict[str, list] = {}
    for rg in realized:
        by_fiscal_year.setdefault(fiscal_year_label(rg.realized_date), []).append(rg)
    realized_tax = sum(capital_gains_tax(group).total_tax for group in by_fiscal_year.values())

    positions: list[Position] = list_open_positions(conn, track=track)
    gross_ending_value = sum(p.market_value(current_prices.get(p.ticker, 0.0)) for p in positions if p.ticker in current_prices)

    current_fy = fiscal_year_label(as_of_date)
    ltcg_realized_this_fy = sum(
        rg.gain for rg in by_fiscal_year.get(current_fy, []) if rg.gain_type == "LTCG" and rg.gain > 0
    )
    remaining_exemption = max(0.0, LTCG_ANNUAL_EXEMPTION - ltcg_realized_this_fy)

    accrued_tax = 0.0
    for position in positions:
        current_price = current_prices.get(position.ticker)
        if current_price is None:
            continue
        for lot in position.lots:
            lot_gain = lot.open_quantity * (current_price - lot.cost_basis_per_unit)
            days = holding_days(lot.purchase_date, as_of_date)
            accrued_tax += accrued_tax_on_unrealized(lot_gain, days, remaining_exemption)
            if classify_gain(days) == "LTCG" and lot_gain > 0:
                remaining_exemption = max(0.0, remaining_exemption - lot_gain)

    post_tax_ending_value = gross_ending_value - accrued_tax

    gross_flows = [*trade_cashflows, CashFlow(date=as_of_date, amount=gross_ending_value)]
    post_tax_flows = [
        *trade_cashflows,
        CashFlow(date=as_of_date, amount=-realized_tax),
        CashFlow(date=as_of_date, amount=post_tax_ending_value),
    ]

    xirr_gross = xirr(gross_flows) if invested_capital > 0 else 0.0
    xirr_post_tax = xirr(post_tax_flows) if invested_capital > 0 else 0.0

    return TrackScorecard(
        track=track,
        as_of_date=as_of_date,
        invested_capital=invested_capital,
        realized_tax=realized_tax,
        accrued_tax_on_unrealized=accrued_tax,
        gross_ending_value=gross_ending_value,
        post_tax_ending_value=post_tax_ending_value,
        xirr_gross=xirr_gross,
        xirr_post_tax=xirr_post_tax,
    )
