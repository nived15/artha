"""Post-July-2024 Indian capital-gains tax on listed equity (plan.md §2.3).

Rates: STCG 20% (held <=12 months), LTCG 12.5% (held >12 months), with a
₹1.25L annual LTCG exemption. Loss set-off follows the standard Indian
rule: a short-term capital loss may offset short- or long-term gains; a
long-term capital loss may only offset long-term gains. Carry-forward of
unused losses across fiscal years is not modeled — Phase 4's paper ledger
only needs one fiscal year's tax at a time; a real, multi-year carry-forward
belongs to a later phase if the paper record shows it matters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from artha.ledger.tax_lots import RealizedGain

STCG_RATE = 0.20
LTCG_RATE = 0.125
LTCG_ANNUAL_EXEMPTION = 125_000.0


@dataclass(frozen=True)
class TaxSummary:
    net_stcg: float          # sum of realized STCG gains/losses, before set-off
    net_ltcg: float          # sum of realized LTCG gains/losses, before set-off
    ltcg_after_offset: float  # LTCG after any STCG-loss set-off
    ltcg_taxable: float       # LTCG after offset and the annual exemption
    stcg_taxable: float       # STCG after any loss set-off (0 if net STCG is a loss)
    stcg_tax: float
    ltcg_tax: float

    @property
    def total_tax(self) -> float:
        return self.stcg_tax + self.ltcg_tax


def fiscal_year_label(iso_date: str) -> str:
    """India's fiscal year: April 1 - March 31, e.g. "FY2025-26" for any date
    from 2025-04-01 through 2026-03-31."""
    d = date.fromisoformat(iso_date)
    if d.month >= 4:
        start_year = d.year
    else:
        start_year = d.year - 1
    return f"FY{start_year}-{str(start_year + 1)[-2:]}"


def capital_gains_tax(realized_gains: list[RealizedGain]) -> TaxSummary:
    """Compute tax owed on a set of realized gains (typically one fiscal year's worth).

    Callers filter `realized_gains` to one fiscal_year_label before calling
    this, since the ₹1.25L LTCG exemption and loss set-off are both
    per-fiscal-year rules.
    """
    net_stcg = sum(rg.gain for rg in realized_gains if rg.gain_type == "STCG")
    net_ltcg = sum(rg.gain for rg in realized_gains if rg.gain_type == "LTCG")

    stcg_loss = -min(0.0, net_stcg)  # magnitude of a net STCG loss, else 0
    ltcg_after_offset = net_ltcg
    if stcg_loss > 0:
        offset = min(stcg_loss, max(0.0, net_ltcg))
        ltcg_after_offset = net_ltcg - offset

    stcg_taxable = max(0.0, net_stcg)
    ltcg_taxable = max(0.0, max(0.0, ltcg_after_offset) - LTCG_ANNUAL_EXEMPTION)

    stcg_tax = stcg_taxable * STCG_RATE
    ltcg_tax = ltcg_taxable * LTCG_RATE

    return TaxSummary(
        net_stcg=net_stcg,
        net_ltcg=net_ltcg,
        ltcg_after_offset=ltcg_after_offset,
        ltcg_taxable=ltcg_taxable,
        stcg_taxable=stcg_taxable,
        stcg_tax=stcg_tax,
        ltcg_tax=ltcg_tax,
    )


def accrued_tax_on_unrealized(unrealized_gain: float, days_held: int, ltcg_exemption_remaining: float) -> float:
    """Estimate the tax that would be owed if an open lot were sold today.

    `ltcg_exemption_remaining` is the ₹1.25L annual LTCG exemption left
    after already-realized LTCG gains for the fiscal year have used their
    share — pass the full 125,000 if no LTCG has been realized yet this
    fiscal year. Only gains (not losses) accrue a positive tax estimate;
    an unrealized loss is not a negative tax liability here.
    """
    if unrealized_gain <= 0:
        return 0.0
    gain_type = "LTCG" if days_held > 365 else "STCG"
    if gain_type == "STCG":
        return unrealized_gain * STCG_RATE
    taxable = max(0.0, unrealized_gain - max(0.0, ltcg_exemption_remaining))
    return taxable * LTCG_RATE
