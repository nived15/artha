"""Canonical feature contract for the rebuilt engine.

The v1 screening code (artha/screening/) read raw Screener values straight
into thresholds, so a field exported as "18" (percent) and one exported as
"0.18" (ratio) were compared against the same constant. This module makes
the unit part of the contract: every feature declares its wire unit once,
values are normalised on the way in, and everything downstream works in
decimals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Unit(str, Enum):
    """Unit of a feature as it arrives from the source export."""

    RATIO = "ratio"          # already a decimal multiple, e.g. D/E 0.4
    PERCENT = "percent"      # arrives as 18.0, stored as 0.18
    CURRENCY_CR = "currency_cr"
    COUNT = "count"
    YEARS = "years"
    TEXT = "text"


# Leverage is the product for these, so EV- and debt-based arithmetic is
# dropped rather than failed (plan.md 5.3a).
LENDING_PROFILES = frozenset({"profile_2_banking", "profile_3_insurance"})


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    unit: Unit
    description: str


def _f(name: str, unit: Unit, description: str) -> tuple[str, FeatureSpec]:
    return name, FeatureSpec(name, unit, description)


FEATURES: dict[str, FeatureSpec] = dict(
    (
        _f("market_cap", Unit.CURRENCY_CR, "Market capitalisation in Rs crore"),
        _f("price", Unit.CURRENCY_CR, "Current market price"),
        _f("pe_ratio", Unit.RATIO, "Trailing price to earnings"),
        _f("price_to_book", Unit.RATIO, "Price to book value"),
        _f("enterprise_value", Unit.CURRENCY_CR, "Market cap + debt - cash"),
        _f("ebit", Unit.CURRENCY_CR, "Earnings before interest and tax"),
        _f("net_working_capital_ex_cash_ex_debt", Unit.CURRENCY_CR, "Greenblatt working capital"),
        _f("net_fixed_assets_ex_goodwill", Unit.CURRENCY_CR, "Greenblatt net fixed assets"),
        _f("roe", Unit.PERCENT, "Return on equity"),
        _f("roce", Unit.PERCENT, "Return on capital employed"),
        _f("opm", Unit.PERCENT, "Operating profit margin"),
        _f("gross_margin", Unit.PERCENT, "Gross margin"),
        _f("debt_to_equity", Unit.RATIO, "Debt to equity"),
        _f("current_ratio", Unit.RATIO, "Current ratio"),
        _f("interest_coverage", Unit.RATIO, "Interest coverage, times"),
        _f("fcf_conversion", Unit.PERCENT, "Free cash flow over net profit"),
        _f("sales_growth_3y", Unit.PERCENT, "3 year sales CAGR"),
        _f("profit_growth_3y", Unit.PERCENT, "3 year profit CAGR"),
        _f("profit_growth_5y", Unit.PERCENT, "5 year profit CAGR"),
        _f("sales_growth_5y", Unit.PERCENT, "5 year sales CAGR"),
        _f("eps_growth_latest_q_yoy", Unit.PERCENT, "Latest quarter EPS growth YoY"),
        _f("eps_growth_ttm_yoy", Unit.PERCENT, "TTM EPS growth versus prior TTM"),
        _f("dividend_yield", Unit.PERCENT, "Trailing dividend yield"),
        _f("promoter_holding", Unit.PERCENT, "Promoter shareholding"),
        _f("promoter_pledge", Unit.PERCENT, "Pledged share of promoter holding"),
        _f("promoter_holding_trend_3y", Unit.PERCENT, "Change in promoter holding over 3 years"),
        _f("roiic_3y", Unit.PERCENT, "Return on incremental invested capital, 3 year"),
        _f("reinvestment_rate", Unit.RATIO, "Share of earnings reinvested"),
        _f("years_since_incorporation", Unit.YEARS, "Age of the company"),
        _f("sector", Unit.TEXT, "Industry label used for peer grouping"),
    )
)

_PERCENT_SCALE = 100.0


def normalise(name: str, raw: float | str | None) -> float | str | None:
    """Convert a raw source value into the engine's internal unit."""
    if raw is None:
        return None
    spec = FEATURES.get(name)
    if spec is None:
        return raw
    if spec.unit is Unit.TEXT:
        return str(raw)
    if not isinstance(raw, (int, float)):
        return None
    if spec.unit is Unit.PERCENT:
        return float(raw) / _PERCENT_SCALE
    return float(raw)


@dataclass(frozen=True)
class FeatureVector:
    """One company's normalised features for one point in time."""

    ticker: str
    profile: str
    as_of: str
    values: dict[str, float | str] = field(default_factory=dict)

    def get(self, name: str) -> float | None:
        value = self.values.get(name)
        return value if isinstance(value, (int, float)) else None

    def text(self, name: str) -> str | None:
        value = self.values.get(name)
        return value if isinstance(value, str) else None

    def has(self, *names: str) -> bool:
        return all(self.get(n) is not None for n in names)

    def missing(self, *names: str) -> tuple[str, ...]:
        return tuple(n for n in names if self.get(n) is None)


def build_feature_vector(
    *,
    ticker: str,
    profile: str,
    as_of: str,
    raw: dict[str, float | str | None],
) -> FeatureVector:
    """Normalise a raw {canonical_name: value} mapping into a FeatureVector.

    Unknown keys are dropped rather than carried through, so a typo in the
    field map surfaces as a missing feature instead of a silently ignored one.
    """
    values: dict[str, float | str] = {}
    for name, raw_value in raw.items():
        if name not in FEATURES:
            continue
        normalised = normalise(name, raw_value)
        if normalised is not None:
            values[name] = normalised
    return FeatureVector(ticker=ticker, profile=profile, as_of=as_of, values=values)
