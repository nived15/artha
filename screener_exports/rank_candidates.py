"""One-off ranking pass over the full profile_1_standard universe.

Not part of the Artha package; a throwaway analysis script to select a
20-stock shortlist (10 Track A + 10 Track B) from the 1,104-row snapshot,
using every Stage-1a-computable field (the snapshot lacks 5yr growth /
EPS-acceleration fields, so the formal growth_gate/davis/lynch screens
can't fully auto-clear -- see track_a.py / track_b.py). This script
hard-excludes genuine red flags (explicit FAIL on computable criteria)
and ranks the rest by the same frameworks' available signals.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

from artha.data.field_map import load_field_map
from artha.screening.loader import build_company_records
from artha.screening.hard_blocks import company_to_greenblatt_inputs, rank_by_greenblatt, fatal_flaw_checklist, promoter_integrity_red_flags
from artha.screening.track_a import quality_gate, growth_gate
from artha.screening.track_b import kedia_smile
from artha.screening.models import Outcome

CSV_PATH = ROOT / "screener_exports" / "artha-profile-1-validation.csv"
FIELD_MAP_PATH = ROOT / "config" / "screener_field_map.toml"

with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

field_map = load_field_map(str(FIELD_MAP_PATH), "profile_1_standard")
records = build_company_records(rows, field_map, arithmetic_profile="profile_1_standard")
greenblatt = rank_by_greenblatt(records)

def has_fail(*results) -> tuple[bool, list[str]]:
    reasons = []
    for r in results:
        for c in r.criteria:
            if c.outcome == Outcome.FAIL:
                reasons.append(f"{r.screen_name}:{c.name}({c.detail})")
    return (len(reasons) > 0, reasons)

track_a_rows = []
track_b_rows = []

for rec in records:
    qg = quality_gate(rec)
    gg = growth_gate(rec)
    ff = fatal_flaw_checklist(rec)
    pi = promoter_integrity_red_flags(rec)
    ks = kedia_smile(rec)

    fail_a, reasons_a = has_fail(qg, ff, pi)
    fail_b, reasons_b = has_fail(ks, ff, pi)

    gb = greenblatt.get(rec.ticker)
    peg = rec.get_float("peg_ratio")
    roe = rec.get_float("roe")
    roce = rec.get_float("roce")
    de = rec.get_float("debt_to_equity")
    opm = rec.get_float("opm")
    sales3 = rec.get_float("sales_growth_3y")
    profit3 = rec.get_float("profit_growth_3y")
    pledge = rec.get_float("promoter_pledge_pct")
    promoter = rec.get_float("promoter_holding_pct")
    ptrend = rec.get_float("promoter_holding_trend_3y")
    mcap = rec.get_float("market_cap")
    pe = rec.get_float("pe_ratio")
    sector = rec.get("sector")

    base_ok = (
        pledge is not None and pledge == 0.0
        and promoter is not None and promoter >= 50
        and (ptrend is None or ptrend >= 0)
        and de is not None and de <= 1.0
        and roe is not None and roe >= 15
        and roce is not None and roce >= 15
    )

    if not fail_a and base_ok and gb is not None:
        track_a_rows.append({
            "ticker": rec.ticker, "sector": sector, "mcap": mcap, "roe": roe, "roce": roce,
            "de": de, "opm": opm, "sales3": sales3, "profit3": profit3, "peg": peg,
            "pe": pe, "promoter": promoter, "ptrend": ptrend, "pledge": pledge,
            "gb_percentile": gb.percentile, "gb_combined_rank": gb.combined_rank,
        })

    smile_ok = (
        mcap is not None and 200 <= mcap <= 5000
        and promoter is not None and promoter >= 40
        and (ptrend is None or ptrend >= 0)
        and pledge is not None and pledge == 0.0
        and de is not None and de <= 1.5
        and roe is not None and roe >= 15
        and profit3 is not None and profit3 >= 15
        and peg is not None and peg > 0
    )
    if not fail_b and smile_ok:
        track_b_rows.append({
            "ticker": rec.ticker, "sector": sector, "mcap": mcap, "roe": roe, "roce": roce,
            "de": de, "opm": opm, "sales3": sales3, "profit3": profit3, "peg": peg,
            "pe": pe, "promoter": promoter, "ptrend": ptrend, "pledge": pledge,
        })

# Track A: rank by Greenblatt combined rank (lower better) -- the plan's own named ranking gate, fully computable here.
track_a_rows.sort(key=lambda r: r["gb_combined_rank"])

# Track B: rank by PEG ascending (cheaper growth first, Lynch buy-zone logic), tie-break by profit growth desc.
track_b_rows.sort(key=lambda r: (r["peg"], -r["profit3"]))

print("=== TRACK A candidates (clean hard-block + quality gate, ranked by Greenblatt) ===")
print(f"total qualifying: {len(track_a_rows)}")
for r in track_a_rows[:15]:
    print(json.dumps(r))

print()
print("=== TRACK B candidates (SMILE band + clean quality, ranked by PEG) ===")
print(f"total qualifying: {len(track_b_rows)}")
for r in track_b_rows[:15]:
    print(json.dumps(r))
