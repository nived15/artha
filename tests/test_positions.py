from __future__ import annotations

import pytest

from artha.db import apply_migrations, connect
from artha.ledger.positions import get_position, list_open_positions
from artha.ledger.tax_lots import record_buy, record_sell


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "artha.db")
    apply_migrations(c)
    yield c
    c.close()


def test_get_position_none_when_flat(conn):
    assert get_position(conn, "ALPHA") is None


def test_get_position_aggregates_multiple_lots(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2024-01-01")
    record_buy(conn, ticker="ALPHA", track="A", quantity=50, price=70.0, trade_date="2024-06-01")

    position = get_position(conn, "ALPHA")
    assert position.quantity == pytest.approx(150.0)
    assert position.cost_basis == pytest.approx(100 * 50.0 + 50 * 70.0)
    assert position.avg_cost_per_unit == pytest.approx((100 * 50.0 + 50 * 70.0) / 150.0)


def test_unrealized_gain_and_market_value(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2024-01-01")
    position = get_position(conn, "ALPHA")
    assert position.market_value(80.0) == pytest.approx(8000.0)
    assert position.unrealized_gain(80.0) == pytest.approx(3000.0)


def test_position_reflects_partial_sell(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2023-01-01")
    record_sell(conn, ticker="ALPHA", quantity=40, price=90.0, trade_date="2025-01-01")
    position = get_position(conn, "ALPHA")
    assert position.quantity == pytest.approx(60.0)
    assert position.cost_basis == pytest.approx(60 * 50.0)


def test_list_open_positions_filters_by_track(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=10, price=10.0, trade_date="2024-01-01")
    record_buy(conn, ticker="BETA", track="B", quantity=10, price=10.0, trade_date="2024-01-01")

    assert {p.ticker for p in list_open_positions(conn, track="A")} == {"ALPHA"}
    assert {p.ticker for p in list_open_positions(conn, track="B")} == {"BETA"}
    assert {p.ticker for p in list_open_positions(conn)} == {"ALPHA", "BETA"}


def test_accrued_tax_liability_ltcg_lot(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2023-01-01")
    position = get_position(conn, "ALPHA")
    # Held well over 12 months as of 2025-01-01; gain = 100*(200-50) = 15,000,
    # fully within the 125,000 exemption -> zero accrued tax.
    tax = position.accrued_tax_liability(200.0, "2025-01-01")
    assert tax == pytest.approx(0.0)


def test_accrued_tax_liability_stcg_lot(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=100, price=50.0, trade_date="2025-01-01")
    position = get_position(conn, "ALPHA")
    # Held under 12 months as of 2025-06-01 -> STCG, no exemption applies.
    tax = position.accrued_tax_liability(80.0, "2025-06-01")
    assert tax == pytest.approx(100 * (80.0 - 50.0) * 0.20)
