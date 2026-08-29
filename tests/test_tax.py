from __future__ import annotations

import pytest

from artha.ledger.tax import (
    LTCG_ANNUAL_EXEMPTION,
    LTCG_RATE,
    STCG_RATE,
    accrued_tax_on_unrealized,
    capital_gains_tax,
    fiscal_year_label,
)
from artha.ledger.tax_lots import RealizedGain


def _rg(gain: float, gain_type: str) -> RealizedGain:
    return RealizedGain(
        realization_id="r", sell_trade_id="t", lot_id="l", ticker="ALPHA", track="A",
        quantity=1, cost_basis=0, proceeds=gain, gain=gain, holding_days=400 if gain_type == "LTCG" else 30,
        gain_type=gain_type, realized_date="2025-06-01",
    )


def test_fiscal_year_label():
    assert fiscal_year_label("2025-04-01") == "FY2025-26"
    assert fiscal_year_label("2026-03-31") == "FY2025-26"
    assert fiscal_year_label("2026-04-01") == "FY2026-27"
    assert fiscal_year_label("2025-01-15") == "FY2024-25"


def test_stcg_taxed_flat_no_exemption():
    summary = capital_gains_tax([_rg(100_000, "STCG")])
    assert summary.stcg_taxable == pytest.approx(100_000)
    assert summary.stcg_tax == pytest.approx(100_000 * STCG_RATE)
    assert summary.ltcg_tax == 0.0


def test_ltcg_under_exemption_is_tax_free():
    summary = capital_gains_tax([_rg(100_000, "LTCG")])
    assert summary.ltcg_taxable == 0.0
    assert summary.ltcg_tax == 0.0


def test_ltcg_above_exemption_taxes_only_the_excess():
    gain = 300_000.0
    summary = capital_gains_tax([_rg(gain, "LTCG")])
    expected_taxable = gain - LTCG_ANNUAL_EXEMPTION
    assert summary.ltcg_taxable == pytest.approx(expected_taxable)
    assert summary.ltcg_tax == pytest.approx(expected_taxable * LTCG_RATE)


def test_stcg_loss_offsets_ltcg_gain():
    # A 40,000 STCG loss plus a 300,000 LTCG gain: the loss offsets LTCG first.
    summary = capital_gains_tax([_rg(-40_000, "STCG"), _rg(300_000, "LTCG")])
    assert summary.stcg_taxable == 0.0
    assert summary.ltcg_after_offset == pytest.approx(260_000)
    assert summary.ltcg_taxable == pytest.approx(260_000 - LTCG_ANNUAL_EXEMPTION)
    assert summary.total_tax == pytest.approx((260_000 - LTCG_ANNUAL_EXEMPTION) * LTCG_RATE)


def test_ltcg_loss_does_not_offset_stcg_gain():
    # A long-term loss may only offset long-term gains, never short-term gains.
    summary = capital_gains_tax([_rg(100_000, "STCG"), _rg(-50_000, "LTCG")])
    assert summary.stcg_taxable == pytest.approx(100_000)
    assert summary.stcg_tax == pytest.approx(100_000 * STCG_RATE)
    assert summary.ltcg_taxable == 0.0


def test_accrued_tax_on_unrealized_loss_is_zero():
    assert accrued_tax_on_unrealized(-1000, 400, LTCG_ANNUAL_EXEMPTION) == 0.0


def test_accrued_tax_on_unrealized_stcg():
    assert accrued_tax_on_unrealized(10_000, 100, LTCG_ANNUAL_EXEMPTION) == pytest.approx(10_000 * STCG_RATE)


def test_accrued_tax_on_unrealized_ltcg_respects_remaining_exemption():
    # Only 50,000 of exemption left; a 200,000 gain is taxed on the excess.
    tax = accrued_tax_on_unrealized(200_000, 400, 50_000)
    assert tax == pytest.approx((200_000 - 50_000) * LTCG_RATE)
