from __future__ import annotations

import pytest

from artha.db import apply_migrations, connect
from artha.ledger.tax_lots import (
    SellDisciplineError,
    classify_gain,
    get_open_lots,
    holding_days,
    list_realized_gains,
    record_buy,
    record_sell,
)


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "artha.db")
    apply_migrations(c)
    yield c
    c.close()


def test_record_buy_creates_open_lot(conn):
    lot = record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2025-01-01")
    assert lot.open_quantity == 100
    assert lot.cost_basis_per_unit == 50.0

    lots = get_open_lots(conn, "ALPHA")
    assert len(lots) == 1
    assert lots[0].lot_id == lot.lot_id


def test_holding_days_and_classification():
    assert holding_days("2025-01-01", "2025-06-01") == 151
    assert classify_gain(151) == "STCG"
    assert classify_gain(365) == "STCG"
    assert classify_gain(366) == "LTCG"


def test_sell_within_12_months_blocked_without_override(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2025-01-01")
    with pytest.raises(SellDisciplineError):
        record_sell(conn, ticker="ALPHA", quantity=50, price=60.0, trade_date="2025-06-01")


def test_sell_within_12_months_allowed_with_override(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2025-01-01")
    realized = record_sell(
        conn, ticker="ALPHA", quantity=50, price=60.0, trade_date="2025-06-01",
        override_reason="thesis broken: accounting fraud alleged",
    )
    assert len(realized) == 1
    assert realized[0].gain_type == "STCG"
    assert realized[0].gain == pytest.approx(500.0)  # 50 * (60-50)


def test_sell_after_12_months_needs_no_override(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2024-01-01")
    realized = record_sell(conn, ticker="ALPHA", quantity=100, price=80.0, trade_date="2025-06-01")
    assert len(realized) == 1
    assert realized[0].gain_type == "LTCG"
    assert realized[0].gain == pytest.approx(3000.0)  # 100 * (80-50)


def test_sell_consumes_lots_fifo_across_two_buys(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2023-01-01")
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=70.0, trade_date="2023-06-01")
    realized = record_sell(conn, ticker="ALPHA", quantity=150, price=90.0, trade_date="2025-01-01")

    assert len(realized) == 2
    first, second = realized
    # FIFO: the oldest (cheapest) lot is consumed first, fully (100 units).
    assert first.quantity == pytest.approx(100.0)
    assert first.cost_basis == pytest.approx(5000.0)
    # The second lot only supplies the remaining 50 units.
    assert second.quantity == pytest.approx(50.0)
    assert second.cost_basis == pytest.approx(3500.0)

    remaining_lots = get_open_lots(conn, "ALPHA")
    assert len(remaining_lots) == 1
    assert remaining_lots[0].open_quantity == pytest.approx(50.0)


def test_sell_more_than_open_quantity_raises(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2023-01-01")
    with pytest.raises(ValueError):
        record_sell(conn, ticker="ALPHA", quantity=200, price=90.0, trade_date="2025-01-01")


def test_list_realized_gains_filters_by_track(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=10, price=10.0, trade_date="2023-01-01")
    record_buy(conn, ticker="BETA", track="B", quantity=10, price=10.0, trade_date="2023-01-01")
    record_sell(conn, ticker="ALPHA", quantity=10, price=20.0, trade_date="2025-01-01")
    record_sell(conn, ticker="BETA", quantity=10, price=20.0, trade_date="2025-01-01")

    assert len(list_realized_gains(conn, track="A")) == 1
    assert len(list_realized_gains(conn, track="B")) == 1
    assert len(list_realized_gains(conn)) == 2
