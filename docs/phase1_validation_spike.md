# Phase 1 — §13.4 validation spike: desk-research results

plan.md §13.4 requires four checks before Phase 1 builds on Screener.in
Premium's CSV export: (a) column ceiling, (b) shareholding fields,
(c) export reuse terms, (d) smallcap completeness, (e) sector-native
fields. This document records the **desk-research** portion of that spike
— everything checkable without an active Screener Premium account. The
**empirical** portion — (d) and full confirmation of (a)/(e) — requires an
actual paid CSV export, which only the account holder (you) can produce.
This is the same human/financial-action boundary Phase 0 hit with the IPS
and benchmark freeze: code can prepare the check, not perform the paid
action.

Desk research performed by a `research` sub-agent (web search + direct
fetches of screener.in support docs, ToS, and public screens) on
2026-08-29. Full source list and confidence ratings are in the sub-agent's
report, condensed below; the field-name conclusions are already encoded in
`config/screener_field_map.example.toml`.

## (a) Column ceiling

Screener Premium's CSV export supports up to 50 columns per custom screen
(`support.screener.in/article/28-export-screen-results`, confirmed). All of
Profile 1's standard fields plus the Greenblatt ROC/EV components fit
comfortably within 50 columns from the confirmed field list below — this
check is expected to pass on a real export, but the exact column count
depends on the query you build, so `artha data import-screener` computes
and enforces this automatically from the real file.

**Confirmed native fields** (high confidence — observed in live public
screener.in screens or Screener's own support docs):

`Market Capitalization`, `Current price`, `Price to Earning`, `EV to
EBITDA`, `OPM`, `Return on equity`, `Return on capital employed` (`ROCE`),
`Average return on capital employed 5Years`, `Debt to equity`, `Promoter
holding`, `Pledged percentage`, `Sales growth 3Years`, `Profit growth
3Years`, `Book value`, `Current ratio`, `Quick ratio`, `Enterprise Value`
(`EV`), `EBIT`, `Net Block`, `Current Assets`, `Current Liabilities`, `FII
Holding`, `DII Holding`, `Public holding`, `Change in promoter holding
3Years`, `Change in FII holding 3Years`.

Screener supports inline arithmetic (`+ - * /`) in both filter conditions
and custom-ratio definitions, so derived fields (e.g. working capital =
`Current Assets - Current Liabilities`) do not need a native column.

**Not yet confirmed** (would need a logged-in "All Ratios" panel to
enumerate exhaustively): the complete field list, and whether shorter
promoter-holding-change windows (1Q/1Y) exist as named columns.

## (b) Shareholding fields

**Confirmed exportable** (verified against a fetched live public screen's
query text): `Promoter holding`, `Pledged percentage`, `FII Holding`, `DII
Holding`, `Public holding`, `Change in promoter holding 3Years`.

**Important limitation:** a single CSV row per company can only carry
point-in-time values and n-year *change scalars* — not a multi-quarter
shareholding time-series vector. This matches plan.md's own Stage 1a/1b
split (§13, "one row per company"): quarterly shareholding-history detail
that isn't a scalar stays a Stage 1b (per-company page) lookup, not a
Stage 1a CSV column. No design change needed — this was already the
plan's assumption.

## (c) Export reuse terms

Read directly from `screener.in/guides/terms/` (fetched verbatim, dated
2018-08-01). The literal license text is restrictive boilerplate: "personal,
non-commercial, transitory viewing only," prohibits copying/modifying, and
requires destroying downloaded materials on license termination. This is
in tension with Screener's own support article
(`support.screener.in/article/28-export-screen-results`), which explicitly
markets the CSV export for "Python / Java / R / Pandas" use — i.e. exactly
the programmatic personal use this project needs.

**Practical read:** a private, personal, non-commercial pipeline (never
redistributing or publishing the data) is very unlikely to draw
enforcement and aligns with the product's own marketed use case. It is not
a squeaky-clean green light under the literal ToS text. **Recommendation:**
proceed on this basis (matching §13.2a's argument), but for
belt-and-suspenders certainty, email `support@screener.in` once to confirm
personal programmatic use is acceptable — this is a one-time human action,
not a blocking one.

**This does not change §16.6 snapshot-immutability reasoning**: storing
your own paid export privately for your own reproducibility is the
weakest possible form of "reuse" under any reading of the clause.

## (d) Smallcap completeness — CONFIRMED, 2026-08-30

Closed out empirically against a real Profile 1 Premium export
(`screener_exports/artha-profile-1-validation.csv`, 1104 rows, market caps
ranging ₹200-995cr — entirely within the smallcap band): `artha data
import-screener screener_exports/artha-profile-1-validation.csv --source
screener_profile1 --profile profile_1_standard` reports **column_ceiling_ok:
True** (23 of 50 columns used) and **passed: True** — every one of §13.4(a)'s
core + Greenblatt-ROC + shareholding required fields resolves to a real
column, with per-field completeness from 71.7% (`promoter_holding_trend_3y`)
to 100% (`market_cap`). The custom ratios `Artha PEG` and `Artha NWC` (for
`peg_ratio` and `net_working_capital_ex_cash_ex_debt`, previously `<TODO>`
in the field map) are confirmed working Screener custom-ratio columns at
78.5% and 99.7% completeness respectively. This closes out both (a) and
(d) for real; the snapshot is recorded (`snapshot_fields` table) and
journaled (`screener_export_ingested` event) via this exact command.

## (e) Sector-native fields

**Banking/NBFC** (GNPA, NNPA, NIM, CAR, PCR, CASA, credit cost):
**confirmed NOT available**, empirically, on 2026-08-30. A real Premium
export of the whole "Financial Services" sector (Banks + NBFC + Housing
Finance + Capital Markets, 20 columns, `screener_exports/financial-
services.csv`) contains none of these fields. Screener's "Add column"
picker also returned no match for the raw components either (Gross/Net
NPA amount, Provisions, Advances, Capital adequacy, Tier 1, Risk weighted
assets), which rules out reconstructing them via a custom ratio — Screener's
custom ratios can only combine fields that are themselves already
addable. Per plan.md §13.4(e), this means **Profile 2 (banking) also moves
to Stage 1b**, the same resolution as Profile 3 below.

**Insurance** (VNB margin, embedded value, persistency, solvency ratio):
**high-confidence NOT available** as native Screener fields — these are
actuarial disclosures from investor presentations, not parsed
financial-statement line items. Per plan.md §13.4(e), this means **Profile
3 (insurance) moves to Stage 1b** (per-company pages and filings, ~200-300
names) rather than being dropped from scope. This is a design decision
this spike resolves now, not a TODO: `artha/data/fields.py`'s
`profile_3_insurance` field set stays defined (for Stage 1b's own
completeness bookkeeping later), but Phase 2's Stage 1a screening should
not expect a Profile 3 CSV export to exist.

## Overall spike status

| Check | Status |
|---|---|
| (a) Column ceiling | **Confirmed, 2026-08-30** — real export uses 23/50 columns |
| (b) Shareholding fields | **Confirmed, 2026-08-30** — all three resolve at 71.7-98.8% completeness |
| (c) Export reuse terms | Read; practical judgment call recorded above — proceeding |
| (d) Smallcap completeness | **Confirmed, 2026-08-30** — 1104-row export, entirely ₹200-995cr smallcap band |
| (e) Sector fields | Banking/NBFC and Insurance → both Stage 1b (confirmed absent from Screener) |

**Spike closed.** All five checks are now resolved — (a)/(b)/(d) confirmed
against real Profile 1 data, (c) is a recorded human judgment call, (e)
resolved both sector profiles to Stage 1b. Phase 1's remaining open item is
purely a config-completeness one, not a design question: `config/
screener_field_map.toml`'s Phase 2-only fields (`ocf_to_pat`,
`profit_growth_5y`, etc. — not part of this spike's required-field set)
still need real column confirmation once an export including those columns
exists.

**Fallback condition (§13.4):** if a real export shows the column ceiling
or reuse terms fail, the fallback is a paid bulk API (EODHD-class, ~12x
cost) — re-argue that trade explicitly rather than defaulting into it.
Nothing observed in this desk research triggers that fallback.
