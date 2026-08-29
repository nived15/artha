"""Screening-specific canonical field names (plan.md §5.3 formulas).

Distinct from artha/data/fields.py, which is scoped to the §13.4
validation spike (column-ceiling, shareholding, sector-field checks).
This module's fields are what the Track A/B Stage 1a screens *read* —
resolved through the same config/screener_field_map.toml mechanism
(artha.data.field_map.load_field_map), since it is already a generic
canonical-name -> CSV-column mapping.
"""

from __future__ import annotations

# Fields already defined for Phase 1 (artha/data/fields.py) that the
# screens also consume: market_cap, price, roce, roe, debt_to_equity,
# opm, sales_growth_3y, profit_growth_3y, pe_ratio, peg_ratio, ebit,
# net_working_capital_ex_cash_ex_debt, net_fixed_assets_ex_goodwill,
# enterprise_value, promoter_holding_pct, promoter_pledge_pct,
# promoter_holding_trend_3y.

# Additional fields Phase 2's screens need, not required by the Phase 1
# spike (so a missing mapping here does not fail the §13.4 spike check —
# it surfaces as NEEDS_STAGE_1B on the specific screen criterion instead).
ADDITIONAL_SCREENING_FIELDS: tuple[str, ...] = (
    "ocf_to_pat",
    "current_ratio",
    "price_to_book",
    "profit_growth_5y",
    "eps_growth_ttm_yoy",
    "eps_growth_latest_q_yoy",
    "gross_margin",
    "interest_coverage",
    "fcf_conversion_pct",
    "years_since_incorporation",
    "analyst_coverage_count",
    "dividend_yield_pct",
    "sector",
)
