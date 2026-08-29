"""FIFO tax-lot engine (plan.md §2.3, §11 Phase 4).

Every BUY creates one tax lot. Every SELL consumes open lots oldest-first
(FIFO — India's standard own-history convention for listed equity) and
produces one `RealizedGain` per lot it touches, classified STCG/LTCG by
holding period. This module does not compute tax owed (see
`artha.ledger.tax`) or aggregate positions (see `artha.ledger.positions`) —
it only owns the ledger-of-record for what was bought, sold, and realized.

Sell discipline (config/ips.md §5): "I will not sell any position within 12
months of purchase unless the thesis has broken." `record_sell` enforces
this as a hard guard — selling any lot held <12 months requires an explicit
`override_reason` (recorded on the trade), rather than silently allowing it.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

# plan.md §2.3: "STCG 20% (held <12 months), LTCG 12.5% (held >12 months)".
# Approximated in whole days since a tax lot only records a purchase date.
LTCG_HOLDING_DAYS_THRESHOLD = 365


class SellDisciplineError(ValueError):
    """Raised when a sell would touch a lot held <12 months without an override."""


@dataclass(frozen=True)
class TaxLot:
    lot_id: str
    ticker: str
    track: str
    quantity: float          # original BUY quantity
    open_quantity: float      # remaining unsold quantity
    cost_basis_per_unit: float
    purchase_date: str        # ISO date
    buy_trade_id: str


@dataclass(frozen=True)
class RealizedGain:
    realization_id: str
    sell_trade_id: str
    lot_id: str
    ticker: str
    track: str
    quantity: float
    cost_basis: float
    proceeds: float
    gain: float
    holding_days: int
    gain_type: str    # "STCG" or "LTCG"
    realized_date: str


def holding_days(purchase_date: str, as_of_date: str) -> int:
    """Whole days held between an ISO purchase date and an ISO as-of date."""
    return (date.fromisoformat(as_of_date) - date.fromisoformat(purchase_date)).days


def classify_gain(days_held: int) -> str:
    """STCG if held <=12 months (365 days), LTCG if held longer — plan.md §2.3."""
    return "LTCG" if days_held > LTCG_HOLDING_DAYS_THRESHOLD else "STCG"


def _row_to_lot(row: sqlite3.Row) -> TaxLot:
    return TaxLot(
        lot_id=row["lot_id"],
        ticker=row["ticker"],
        track=row["track"],
        quantity=row["quantity"],
        open_quantity=row["open_quantity"],
        cost_basis_per_unit=row["cost_basis_per_unit"],
        purchase_date=row["purchase_date"],
        buy_trade_id=row["buy_trade_id"],
    )


def record_buy(
    conn: sqlite3.Connection,
    *,
    ticker: str,
    track: str,
    quantity: float,
    price: float,
    trade_date: str,
    note: str | None = None,
) -> TaxLot:
    """Record a BUY: one trade row + one new, fully-open tax lot."""
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if price <= 0:
        raise ValueError("price must be > 0")

    trade_id = str(uuid.uuid4())
    lot_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with conn:
        conn.execute(
            """
            INSERT INTO trades (trade_id, ticker, track, side, quantity, price, trade_date, note, created_at)
            VALUES (?, ?, ?, 'BUY', ?, ?, ?, ?, ?)
            """,
            (trade_id, ticker, track, quantity, price, trade_date, note, now),
        )
        conn.execute(
            """
            INSERT INTO tax_lots
                (lot_id, ticker, track, quantity, open_quantity, cost_basis_per_unit, purchase_date, buy_trade_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (lot_id, ticker, track, quantity, quantity, price, trade_date, trade_id, now),
        )

    return TaxLot(
        lot_id=lot_id,
        ticker=ticker,
        track=track,
        quantity=quantity,
        open_quantity=quantity,
        cost_basis_per_unit=price,
        purchase_date=trade_date,
        buy_trade_id=trade_id,
    )


def get_open_lots(conn: sqlite3.Connection, ticker: str) -> list[TaxLot]:
    """Open lots for one ticker, oldest first (FIFO order)."""
    rows = conn.execute(
        """
        SELECT lot_id, ticker, track, quantity, open_quantity, cost_basis_per_unit, purchase_date, buy_trade_id
        FROM tax_lots
        WHERE ticker = ? AND open_quantity > 0
        ORDER BY purchase_date ASC, rowid ASC
        """,
        (ticker,),
    ).fetchall()
    return [_row_to_lot(r) for r in rows]


def record_sell(
    conn: sqlite3.Connection,
    *,
    ticker: str,
    quantity: float,
    price: float,
    trade_date: str,
    override_reason: str | None = None,
) -> list[RealizedGain]:
    """Record a SELL: consume open lots FIFO, producing one RealizedGain per lot touched.

    Raises SellDisciplineError if any lot that would be touched has been
    held <12 months and no override_reason is given (config/ips.md §5).
    Raises ValueError if quantity exceeds total open quantity for the ticker.
    """
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if price <= 0:
        raise ValueError("price must be > 0")

    open_lots = get_open_lots(conn, ticker)
    total_open = sum(lot.open_quantity for lot in open_lots)
    if quantity > total_open + 1e-9:
        raise ValueError(f"cannot sell {quantity} of {ticker}; only {total_open} open")

    # Simulate the FIFO consumption first so we can check sell discipline
    # against every lot that would be touched before writing anything.
    remaining = quantity
    plan: list[tuple[TaxLot, float, int, str]] = []  # (lot, qty_from_lot, days_held, gain_type)
    for lot in open_lots:
        if remaining <= 1e-9:
            break
        qty_from_lot = min(lot.open_quantity, remaining)
        days_held = holding_days(lot.purchase_date, trade_date)
        gain_type = classify_gain(days_held)
        plan.append((lot, qty_from_lot, days_held, gain_type))
        remaining -= qty_from_lot

    # Any STCG-classified lot in the plan is, by definition, held <=12 months.
    too_new = [lot.lot_id for lot, _, _, gtype in plan if gtype == "STCG"]
    if too_new and override_reason is None:
        raise SellDisciplineError(
            f"selling {ticker} would touch lot(s) held <12 months ({too_new}); "
            "pass override_reason if the thesis has broken (config/ips.md §5)"
        )

    trade_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    track = open_lots[0].track if open_lots else ""
    realized: list[RealizedGain] = []

    with conn:
        conn.execute(
            """
            INSERT INTO trades (trade_id, ticker, track, side, quantity, price, trade_date, note, created_at)
            VALUES (?, ?, ?, 'SELL', ?, ?, ?, ?, ?)
            """,
            (trade_id, ticker, track, quantity, price, trade_date, override_reason, now),
        )
        for lot, qty_from_lot, days_held, gain_type in plan:
            cost_basis = qty_from_lot * lot.cost_basis_per_unit
            proceeds = qty_from_lot * price
            gain = proceeds - cost_basis
            realization_id = str(uuid.uuid4())
            conn.execute(
                "UPDATE tax_lots SET open_quantity = open_quantity - ? WHERE lot_id = ?",
                (qty_from_lot, lot.lot_id),
            )
            conn.execute(
                """
                INSERT INTO realized_gains
                    (realization_id, sell_trade_id, lot_id, ticker, track, quantity, cost_basis, proceeds, gain, holding_days, gain_type, realized_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    realization_id,
                    trade_id,
                    lot.lot_id,
                    ticker,
                    lot.track,
                    qty_from_lot,
                    cost_basis,
                    proceeds,
                    gain,
                    days_held,
                    gain_type,
                    trade_date,
                ),
            )
            realized.append(
                RealizedGain(
                    realization_id=realization_id,
                    sell_trade_id=trade_id,
                    lot_id=lot.lot_id,
                    ticker=ticker,
                    track=lot.track,
                    quantity=qty_from_lot,
                    cost_basis=cost_basis,
                    proceeds=proceeds,
                    gain=gain,
                    holding_days=days_held,
                    gain_type=gain_type,
                    realized_date=trade_date,
                )
            )

    return realized


def list_realized_gains(conn: sqlite3.Connection, *, ticker: str | None = None, track: str | None = None) -> list[RealizedGain]:
    """All realized gains, optionally filtered by ticker and/or track."""
    query = "SELECT * FROM realized_gains WHERE 1=1"
    params: list[str] = []
    if ticker is not None:
        query += " AND ticker = ?"
        params.append(ticker)
    if track is not None:
        query += " AND track = ?"
        params.append(track)
    query += " ORDER BY realized_date ASC"
    rows = conn.execute(query, params).fetchall()
    return [
        RealizedGain(
            realization_id=r["realization_id"],
            sell_trade_id=r["sell_trade_id"],
            lot_id=r["lot_id"],
            ticker=r["ticker"],
            track=r["track"],
            quantity=r["quantity"],
            cost_basis=r["cost_basis"],
            proceeds=r["proceeds"],
            gain=r["gain"],
            holding_days=r["holding_days"],
            gain_type=r["gain_type"],
            realized_date=r["realized_date"],
        )
        for r in rows
    ]
