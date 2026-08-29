"""Canonical required-field spec for the §13.4 validation spike.

This is *not* a live Screener.in schema — it is the set of canonical fields
plan.md §5.3/§5.4 needs, independent of any vendor's column names. The
actual Screener column each canonical field maps to is a per-user detail
(the vendor's UI wording drifts and custom ratios can be renamed), so that
mapping lives in a separate, user-editable file: config/screener_field_map.toml
(see config/screener_field_map.example.toml for the desk-research starting
point). Keeping the two separate means a vendor renaming a column only
requires editing the map, not this spec.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequiredField:
    """One field the screening formulas in plan.md §5.3/§5.4 depend on."""

    canonical_name: str
    description: str
    category: str          # e.g. "core", "greenblatt_roc", "shareholding", "banking", "insurance"
    required_for: tuple[str, ...]  # formula/hard-block names that consume it


# §13.4(a): standard Profile 1 fields every Track A/B Stage 1a screen needs,
# plus the Greenblatt ROC and enterprise-value components — "the binding
# constraint on the whole design" per §13.4.
CORE_REQUIRED_FIELDS: tuple[RequiredField, ...] = (
    RequiredField("market_cap", "Market capitalization", "core", ("§5.1 liquidity floor",)),
    RequiredField("price", "Current market price", "core", ("§5.1", "buy-below price sizing")),
    RequiredField("roce", "Return on capital employed", "core", ("Agrawal QGLP", "Terry Smith")),
    RequiredField("roe", "Return on equity", "core", ("Buffett/Munger moat proxy",)),
    RequiredField("debt_to_equity", "Debt to equity ratio", "core", ("Graham", "Kedia SMILE")),
    RequiredField("opm", "Operating profit margin", "core", ("Terry Smith", "Davis")),
    RequiredField("sales_growth_3y", "3-year sales growth (reported)", "core", ("Davis acceleration test", "Lynch PEG")),
    RequiredField("profit_growth_3y", "3-year profit growth (reported)", "core", ("Davis acceleration test", "Lynch PEG")),
    RequiredField("pe_ratio", "Price to earnings ratio", "core", ("Graham", "Davis", "Lynch PEG")),
    RequiredField("peg_ratio", "PEG ratio (or its native inputs)", "core", ("Lynch PEG")),
    # Greenblatt Magic Formula ROC + EV — §13.4(a)'s binding constraint.
    RequiredField("ebit", "Earnings before interest and tax", "greenblatt_roc", ("Greenblatt ROC",)),
    RequiredField(
        "net_working_capital_ex_cash_ex_debt",
        "Net working capital, excluding excess cash and short-term debt",
        "greenblatt_roc",
        ("Greenblatt ROC",),
    ),
    RequiredField(
        "net_fixed_assets_ex_goodwill",
        "Net fixed assets, excluding goodwill",
        "greenblatt_roc",
        ("Greenblatt ROC",),
    ),
    RequiredField("enterprise_value", "Market cap + total debt - cash", "greenblatt_roc", ("Greenblatt earnings yield", "Pabrai asymmetry gate")),
)

# §13.4(b): shareholding fields gate both tracks and three §5.4 hard blocks.
SHAREHOLDING_REQUIRED_FIELDS: tuple[RequiredField, ...] = (
    RequiredField("promoter_holding_pct", "Promoter holding %", "shareholding", ("§5.4 hard blocks",)),
    RequiredField("promoter_pledge_pct", "Promoter pledged %", "shareholding", ("§5.4 hard blocks", "§13.3a")),
    RequiredField("promoter_holding_trend_3y", "3-year promoter holding trend", "shareholding", ("§5.4 hard blocks",)),
)

# §13.4(e): sector-native fields for §5.3a Profiles 2-3. If these are
# missing from Screener, §5.3a moves these profiles to Stage 1b rather than
# dropping the sector — see plan.md §13.4(e).
BANKING_SECTOR_FIELDS: tuple[RequiredField, ...] = (
    RequiredField("gnpa_pct", "Gross NPA %", "banking", ("§5.3a Profile 2",)),
    RequiredField("nnpa_pct", "Net NPA %", "banking", ("§5.3a Profile 2",)),
    RequiredField("nim_pct", "Net interest margin", "banking", ("§5.3a Profile 2",)),
    RequiredField("car_tier1_pct", "Capital adequacy ratio / Tier-1", "banking", ("§5.3a Profile 2",)),
    RequiredField("provision_coverage_pct", "Provision coverage ratio", "banking", ("§5.3a Profile 2",)),
    RequiredField("casa_pct", "CASA ratio", "banking", ("§5.3a Profile 2",)),
    RequiredField("credit_cost_pct", "Credit cost", "banking", ("§5.3a Profile 2",)),
)

INSURANCE_SECTOR_FIELDS: tuple[RequiredField, ...] = (
    RequiredField("vnb_margin_pct", "Value of new business margin", "insurance", ("§5.3a Profile 3",)),
    RequiredField("embedded_value", "Embedded value", "insurance", ("§5.3a Profile 3",)),
    RequiredField("persistency_pct", "Policy persistency %", "insurance", ("§5.3a Profile 3",)),
    RequiredField("solvency_ratio", "Solvency ratio", "insurance", ("§5.3a Profile 3",)),
)

# Named "arithmetic profiles" per §5.3a — one export per profile, same
# snapshot date/hashing rules, concatenated into one ranked universe.
PROFILE_FIELD_SETS: dict[str, tuple[RequiredField, ...]] = {
    "profile_1_standard": CORE_REQUIRED_FIELDS + SHAREHOLDING_REQUIRED_FIELDS,
    "profile_2_banking": CORE_REQUIRED_FIELDS + SHAREHOLDING_REQUIRED_FIELDS + BANKING_SECTOR_FIELDS,
    "profile_3_insurance": CORE_REQUIRED_FIELDS + SHAREHOLDING_REQUIRED_FIELDS + INSURANCE_SECTOR_FIELDS,
}


def required_fields_for_profile(profile: str) -> tuple[RequiredField, ...]:
    """Look up the required-field set for a named §5.3a profile.

    Falls back to the standard Profile 1 set for unknown profile names
    (e.g. ad-hoc/custom screens) rather than raising, since the caller may
    legitimately be validating a non-standard export.
    """
    return PROFILE_FIELD_SETS.get(profile, PROFILE_FIELD_SETS["profile_1_standard"])
