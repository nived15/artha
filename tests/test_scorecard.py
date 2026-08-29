from __future__ import annotations

import pytest

from artha.db import apply_migrations, connect
from artha.ledger.scorecard import (
    BenchmarkComparison,
    CashFlow,
    TwrPoint,
    annualize,
    compare_to_benchmark,
    fund_annualized_return,
    fund_total_return,
    time_weighted_return,
    track_scorecard,
    xirr,
)
from artha.ledger.tax_lots import record_buy, record_sell


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "artha.db")
    apply_migrations(c)
    yield c
    c.close()


# --- xirr: exact hand-computed reconciliation -------------------------------
# Invest 100,000 on day 0; the position is worth 150,000 exactly 365 days
# later. NPV(r) = -100000 + 150000/(1+r) = 0 => r = 0.5 exactly.

def test_xirr_single_buy_single_sale_reconciles_by_hand():
    cashflows = [
        CashFlow(date="2023-01-01", amount=-100_000.0),
        CashFlow(date="2024-01-01", amount=150_000.0),
    ]
    rate = xirr(cashflows)
    assert rate == pytest.approx(0.5, abs=1e-4)


def test_xirr_requires_mixed_signs():
    with pytest.raises(ValueError):
        xirr([CashFlow(date="2024-01-01", amount=100.0), CashFlow(date="2025-01-01", amount=100.0)])


# --- time_weighted_return: exact hand-computed reconciliation ---------------
# Contribute 100. It grows 10% to 110, then 50 is withdrawn (60 remains
# invested), which grows another 10% to 66. TWR = 1.10 * 1.10 - 1 = 0.21,
# independent of the withdrawal's size or timing (that's the point of TWR).

def test_time_weighted_return_reconciles_by_hand():
    points = [
        TwrPoint(date="2024-01-01", value_before_cashflow=0.0, cashflow=100.0),
        TwrPoint(date="2024-07-01", value_before_cashflow=110.0, cashflow=-50.0),
        TwrPoint(date="2025-01-01", value_before_cashflow=66.0, cashflow=0.0),
    ]
    assert time_weighted_return(points) == pytest.approx(0.21, abs=1e-9)


def test_annualize_two_year_double_is_approximately_41_pct():
    # A 2x over 2 years (730 days) is ~41.4% CAGR — the same "2x in 2 years"
    # figure config/ips.md and plan.md §4 use for Track B's CAGR band.
    assert annualize(1.0, 730) == pytest.approx(0.4142, abs=1e-3)


# --- benchmark comparison ----------------------------------------------------

def test_fund_total_and_annualized_return():
    series = [("2024-01-01", 100.0), ("2025-01-01", 110.0)]
    assert fund_total_return(series) == pytest.approx(0.10)
    assert fund_annualized_return(series) == pytest.approx(0.10, abs=1e-3)


def test_compare_to_benchmark_beats_both():
    result = compare_to_benchmark(sleeve_return=0.20, index_return=0.12, factor_return=0.15)
    assert isinstance(result, BenchmarkComparison)
    assert result.beats_index and result.beats_factor
    assert result.beats_benchmark_set


def test_compare_to_benchmark_one_component_fails_whole_set():
    # config/ips.md §3: beating one component while trailing the other is a loss.
    result = compare_to_benchmark(sleeve_return=0.13, index_return=0.12, factor_return=0.15)
    assert result.beats_index and not result.beats_factor
    assert not result.beats_benchmark_set


# --- track_scorecard: full pipeline reconciliation ---------------------------
# ALPHA: bought 1000 @ 100 (2023-01-01), sold 1000 @ 250 (2025-01-01).
#   Realized LTCG = 1000*(250-100) = 150,000, in FY2024-25.
#   Tax: (150,000 - 125,000 exemption) * 12.5% = 3,125.
# BETA: bought 1000 @ 100 (2023-01-01), still open. Marked at 300 as of
#   2025-06-01 (FY2025-26, no LTCG realized yet this FY, full exemption free).
#   Unrealized LTCG = 1000*(300-100) = 200,000.
#   Accrued tax: (200,000 - 125,000 exemption) * 12.5% = 9,375.

def test_track_scorecard_reconciles_by_hand(conn):
    record_buy(conn, ticker="ALPHA", track="A", quantity=1000, price=100.0, trade_date="2023-01-01")
    record_sell(conn, ticker="ALPHA", quantity=1000, price=250.0, trade_date="2025-01-01")
    record_buy(conn, ticker="BETA", track="A", quantity=1000, price=100.0, trade_date="2023-01-01")

    card = track_scorecard(conn, track="A", as_of_date="2025-06-01", current_prices={"BETA": 300.0})

    assert card.invested_capital == pytest.approx(200_000.0)
    assert card.realized_tax == pytest.approx(3_125.0)
    assert card.accrued_tax_on_unrealized == pytest.approx(9_375.0)
    assert card.gross_ending_value == pytest.approx(300_000.0)
    assert card.post_tax_ending_value == pytest.approx(300_000.0 - 9_375.0)

    # The post-tax return must be lower than the gross return (tax is a drag,
    # never a subsidy), and each reported rate must actually zero its own NPV.
    assert card.xirr_post_tax < card.xirr_gross

    def npv(cashflows, rate):
        from datetime import date
        t0 = date.fromisoformat(min(c.date for c in cashflows))
        return sum(c.amount / (1 + rate) ** ((date.fromisoformat(c.date) - t0).days / 365.0) for c in cashflows)

    gross_flows = [
        CashFlow("2023-01-01", -100_000.0),
        CashFlow("2025-01-01", 250_000.0),
        CashFlow("2023-01-01", -100_000.0),
        CashFlow("2025-06-01", 300_000.0),
    ]
    assert npv(gross_flows, card.xirr_gross) == pytest.approx(0.0, abs=1.0)


def test_track_scorecard_with_no_trades_returns_zeroes(conn):
    card = track_scorecard(conn, track="A", as_of_date="2025-06-01", current_prices={})
    assert card.invested_capital == 0.0
    assert card.xirr_gross == 0.0
    assert card.xirr_post_tax == 0.0
