"""Position aggregation over open tax lots (plan.md §11 Phase 4).

A Position is the current, aggregated view of one ticker's open tax lots —
what artha's own book says you hold, before any live broker reconciliation
(Phase 6). Unrealized gain/loss and the accrued tax estimate are both
computed against a caller-supplied current price, since this ledger has no
live price feed of its own (a Screener snapshot's `price` field, or a
manually entered mark, both work as that input).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from artha.ledger.tax import accrued_tax_on_unrealized
from artha.ledger.tax_lots import TaxLot, classify_gain, get_open_lots, holding_days


@dataclass(frozen=True)
class Position:
    ticker: str
    track: str
    quantity: float
    cost_basis: float          # total cost basis across all open lots
    lots: tuple[TaxLot, ...]

    @property
    def avg_cost_per_unit(self) -> float:
        return self.cost_basis / self.quantity if self.quantity else 0.0

    def market_value(self, current_price: float) -> float:
        return self.quantity * current_price

    def unrealized_gain(self, current_price: float) -> float:
        return self.market_value(current_price) - self.cost_basis

    def accrued_tax_liability(self, current_price: float, as_of_date: str, *, ltcg_exemption_remaining: float = 125_000.0) -> float:
        """Sum of the tax that would be owed if every open lot were sold today.

        Each lot is classified STCG/LTCG independently by its own holding
        period; `ltcg_exemption_remaining` is shared across all of this
        position's LTCG lots (pass the portfolio-wide remaining exemption
        for a correct multi-position estimate — see artha.ledger.scorecard).
        """
        remaining_exemption = ltcg_exemption_remaining
        total = 0.0
        for lot in self.lots:
            lot_gain = lot.open_quantity * (current_price - lot.cost_basis_per_unit)
            days = holding_days(lot.purchase_date, as_of_date)
            tax = accrued_tax_on_unrealized(lot_gain, days, remaining_exemption)
            if classify_gain(days) == "LTCG" and lot_gain > 0:
                remaining_exemption = max(0.0, remaining_exemption - lot_gain)
            total += tax
        return total


def get_position(conn: sqlite3.Connection, ticker: str) -> Position | None:
    """Aggregate one ticker's open lots into a Position, or None if flat."""
    lots = get_open_lots(conn, ticker)
    if not lots:
        return None
    quantity = sum(lot.open_quantity for lot in lots)
    cost_basis = sum(lot.open_quantity * lot.cost_basis_per_unit for lot in lots)
    return Position(ticker=ticker, track=lots[0].track, quantity=quantity, cost_basis=cost_basis, lots=tuple(lots))


def list_open_positions(conn: sqlite3.Connection, *, track: str | None = None) -> list[Position]:
    """All tickers with at least one open lot, aggregated into Positions."""
    query = "SELECT DISTINCT ticker FROM tax_lots WHERE open_quantity > 0"
    params: list[str] = []
    if track is not None:
        query += " AND track = ?"
        params.append(track)
    tickers = [row["ticker"] for row in conn.execute(query, params).fetchall()]
    positions = [get_position(conn, ticker) for ticker in tickers]
    return [p for p in positions if p is not None]
