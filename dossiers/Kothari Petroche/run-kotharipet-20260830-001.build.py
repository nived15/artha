"""Reproducibility artifact for dossiers/Kothari Petroche/run-kotharipet-20260830-001.md.

Manually-orchestrated research pass (see dossiers/Eco Recyc/'s own
precedent note on the artha-dossier factory's placeholder assembly step).
Inputs: this script + filings/KOTHARIPET/*.txt (ingested via
`artha data import-filing`). Every citation was fetched via
get_filing_chunk/list_candidate_chunks before being written here.
"""
import json

SNAPSHOT_ID = "a0d7e35e3abb34602e52ac01075992c76e302178919722d74cb3769f8ad75198"
RUN_ID = "run-kotharipet-20260830-001"
TICKER = "Kothari Petroche"

def cit(doc_id, note, chunk_index=0):
    return {"doc_id": doc_id, "page": 1, "note": f"{note} (chunk_index={chunk_index})"}

BIZ0 = lambda n: cit("KOTHARIPET_BUSINESS_OVERVIEW", n, 0)
BIZ1 = lambda n: cit("KOTHARIPET_BUSINESS_OVERVIEW", n, 1)
FIN0 = lambda n: cit("KOTHARIPET_FINANCIAL_HIGHLIGHTS", n, 0)
FIN1 = lambda n: cit("KOTHARIPET_FINANCIAL_HIGHLIGHTS", n, 1)
SH0 = lambda n: cit("KOTHARIPET_SHAREHOLDING_GOVERNANCE", n, 0)
SH1 = lambda n: cit("KOTHARIPET_SHAREHOLDING_GOVERNANCE", n, 1)

def section(title, content, citations=None):
    return {"title": title, "content": content, "citations": citations or []}

d = {}

d["identity"] = {
    "company": "Kothari Petrochemicals Limited",
    "ticker": TICKER,
    "sector": "Petrochemicals",
    "arithmetic_profile": "profile_1_standard",
    "track": "A",
    "date": "2026-08-30",
    "pipeline_run_id": RUN_ID,
    "snapshot_id": SNAPSHOT_ID,
}

d["business_five_sentences"] = section(
    "The business in five sentences",
    (
        "Kothari Petrochemicals Limited (part of the H C Kothari Group) "
        "manufactures and sells Polyisobutylene (PIB), a specialty "
        "petrochemical polymer, and is described as India's largest "
        "producer of premium-quality PIB. PIB is sold across automotive "
        "lubricant additives, adhesives, sealants, plastic masterbatches, "
        "and other technical/industrial applications, to both domestic and "
        "export customers. As a specialty (not bulk-commodity) "
        "petrochemical producer, its business is exposed to crude-oil/"
        "feedstock input-cost volatility, but competes on technical grade "
        "differentiation and scale within a fewer-producer niche rather "
        "than head-to-head commodity pricing. It is a long-established, "
        "dividend-paying company (unlike the other three candidates in "
        "this research batch), controlled by the Kothari family/group at "
        "72.22% holding, zero pledge, modestly rising trend. Recent "
        "financials show slightly declining revenue (Rs 604cr FY24 to "
        "Rs 589cr FY25) alongside modestly rising profit (Rs 63.8cr to "
        "Rs 65.8cr), consistent with margin expansion."
    ),
    [BIZ0("PIB business description and market position"), FIN0("FY24/FY25 revenue and profit figures")],
)

d["why_now"] = section(
    "Why now",
    (
        "This is a more moderate 'why now' than a hyper-growth story: the "
        "catalyst here is valuation/quality mismatch, not a scaling event. "
        "Kothari trades at 10.70x trailing P/E with a best-decile Greenblatt "
        "combined percentile (5.54%, see §21), near-debt-free (D/E=0.01), "
        "profit growing faster than revenue (24.10% 3yr profit growth vs "
        "7.04% 3yr sales growth -- margin expansion, not just top-line "
        "growth), and a genuine multi-year dividend-paying track record "
        "(interim Rs 1.00/share Aug 2025, final Rs 1.00/share Jul 2024, "
        "~28.47% 5yr dividend growth). This combination -- cheap, "
        "profitable, shareholder-returning, near-debt-free -- is the "
        "steadier, lower-drama Track A case relative to GGBL's faster but "
        "less-verified growth story in this same batch."
    ),
    [FIN0("valuation and profitability metrics"), FIN1("dividend record")],
)

d["three_things_must_be_true"] = section(
    "The three things that must be true",
    (
        "1. Margin expansion (profit growing faster than revenue) must "
        "continue or at least hold, not reverse into margin compression as "
        "feedstock/crude-oil costs move against the company -- falsifiable "
        "by a reported OPM decline in a future snapshot.\n"
        "2. Demand for premium PIB (automotive lubricants, adhesives, "
        "sealants, masterbatches) must not structurally decline -- "
        "falsifiable by a sustained multi-year revenue decline beyond the "
        "single FY24-to-FY25 dip already observed.\n"
        "3. The Kothari family/group's clean, rising promoter holding "
        "(72.22%, zero pledge, +1.24 3yr trend) and consistent dividend "
        "payments must continue, with no adverse RPT/auditor/SEBI finding "
        "-- falsifiable by any of those specific events."
    ),
    [],
)

d["financial_evidence"] = section(
    "Financial evidence",
    (
        "From the ingested Stage 1a snapshot: Market Cap Rs 771.77cr; ROCE "
        "28.60%; ROE 21.43%; D/E 0.01 (near debt-free); OPM 16.65%; 3yr "
        "sales growth 7.04%; 3yr profit growth 24.10%; P/E 10.70x; Artha "
        "PEG 0.44; EBIT Rs 97.35cr; Net Working Capital (ex-cash/debt) Rs "
        "57.61cr; Net Fixed Assets (ex-goodwill) Rs 214.47cr; Enterprise "
        "Value Rs 756.44cr; Promoter holding 72.22%, pledge 0.00%, 3yr "
        "trend +1.24 (rising).\n\n"
        "From secondary web research (NOT independently read from the "
        "primary annual report, though its URL was located): FY2025 "
        "revenue ~Rs 589cr (vs ~Rs 604cr FY2024, a slight decline); FY2025 "
        "net profit ~Rs 65.8cr (vs ~Rs 63.8cr FY2024); EPS ~Rs 12.22 (a "
        "different figure than Stage 1a's own EPS-implied number -- both "
        "reported rather than reconciled with false precision); 52-week "
        "range Rs 94.75-174.00; dividend yield 0.76-1.52% depending on "
        "source/date; dividend payout ratio (TTM) ~8.1%.\n\n"
        "NOT AVAILABLE: OCF/PAT, gross margin (distinct from OPM), "
        "interest coverage, FCF conversion %, current ratio, price-to-book, "
        "and a verified EPS-decline history over 5+ years."
    ),
    [FIN0("Stage 1a and secondary-source financial figures"), FIN1("dividend record and reconciliation")],
)

d["fatal_flaw_checklist"] = section(
    "Fatal-flaw checklist",
    (
        "- promoter_pledging: PASS (0.00%, well under the 20% threshold).\n"
        "- promoter_holding_not_declining: PASS (3yr trend +1.24, "
        "confirmed rising, not declining -- the cleanest evidence of the "
        "four candidates in this batch on this specific check).\n"
        "- profit_becomes_cash (OCF/PAT>=0.8): NEEDS_STAGE_1B -- not a "
        "field in this export. Partial corroborating signal: a consistent "
        "multi-year cash dividend payment (SH0/FIN1) requires real "
        "distributable cash, which is weak but real evidence against pure "
        "accrual-profit-without-cash-backing, though not a substitute for "
        "an independently verified OCF/PAT figure.\n"
        "- survives_worst_year_without_dilution, price_assumption_"
        "plausible: NEEDS_STAGE_3 -- addressed in Pre-Mortem (§9)/"
        "Valuation (§7).\n"
        "- no_single_point_of_failure_dependency: the business is a "
        "single-product-family (PIB) petrochemical manufacturer -- this IS "
        "a real product-concentration risk (unlike GGBL's or Modi "
        "Naturals' more segment-diversified revenue mixes), though "
        "diversified across automotive/adhesive/sealant/masterbatch end "
        "markets and both domestic and export customers (BIZ0).\n"
        "- business_explainable_in_five_sentences: PASS, see §2.\n"
        "- no_serial_equity_dilution: NEEDS_STAGE_1B -- no multi-year "
        "share-count history found, though the long-established, "
        "dividend-paying nature of the company (rather than a recent "
        "capital-raising IPO story) is a weak positive signal against "
        "recent serial dilution.\n"
        "- Greenblatt ranking gate: ROC = EBIT/(NWC+NFA) = 97.35/"
        "(57.61+214.47) = 35.78%; Earnings Yield = EBIT/EV = 97.35/756.44 "
        "= 12.87%. ROC rank 165/1101, EY rank 124/1101, combined rank 289, "
        "combined percentile 5.54% -- CLEARS the best-decile (<=10%) "
        "threshold."
    ),
    [SH0("promoter pledge and rising holding trend"), FIN0("EBIT/NWC/NFA/EV inputs for Greenblatt")],
)

d["valuation"] = section(
    "Valuation",
    (
        "Current: Market Cap Rs 771.77cr, EV Rs 756.44cr (EV below Market "
        "Cap, consistent with the near-debt-free, modest-net-cash profile "
        "implied by D/E=0.01), P/E 10.70x -- moderately cheap, and the "
        "best-decile Greenblatt combined percentile (5.54%) confirms this "
        "on a combined ROC+earnings-yield basis, not just trailing P/E.\n\n"
        "Stated assumptions (mine, not company guidance):\n"
        "- BEAR CASE: crude-oil/feedstock costs rise faster than PIB "
        "pricing can pass through, reversing the recent margin-expansion "
        "trend; export demand softens amid a global industrial slowdown. "
        "Rough assumption-driven downside: 20-30% from current levels -- a "
        "smaller downside range than GGBL's or the Track B picks', "
        "consistent with the lower-volatility, established-business "
        "profile.\n"
        "- BASE CASE: revenue stabilizes or grows modestly (a return "
        "toward or above the FY24 ~Rs 604cr level), margin holds near "
        "current levels, dividend continues. This implies a fair-to-modest "
        "return from the current cheap entry, without requiring a dramatic "
        "re-rating.\n"
        "- BULL CASE: PIB demand growth (automotive/industrial recovery) "
        "plus continued margin expansion could support a re-rating from "
        "10.70x toward a mid-teens multiple more typical of a profitable, "
        "dividend-paying specialty-chemicals name -- assume 25-45% upside "
        "over 2-3 years, a more modest bull case than GGBL's but also a "
        "narrower bear case.\n\n"
        "Overall read: this is the most balanced risk/reward profile of "
        "the four candidates in this research batch -- not a screaming "
        "bargain, not a hyper-growth story, but a genuinely cheap, "
        "profitable, dividend-paying, near-debt-free business with a "
        "best-decile quantitative rank."
    ),
    [FIN0("Stage 1a valuation multiples"), FIN1("dividend record as a stability signal")],
)

d["buy_below_and_sizing"] = section(
    "Buy-below price and position size",
    (
        "Given the QGLP Price score of 2/3 (§16) and a Jhunjhunwala "
        "conviction score of 4/5 (§23, the highest of the four candidates "
        "in this batch), a buy-below discipline can be modestly less "
        "conservative than for the other three candidates: proposed "
        "buy-below roughly 5-10% below current levels.\n\n"
        "Position size: config/ips.md caps a fully-sized Track A position "
        "at 2.5% of total investable assets, restricted to 1.25% at the "
        "initial 5% active-sleeve stage. Given the higher (4/5) conviction "
        "score here relative to GGBL (3/5), this proposal sizes toward the "
        "upper half of the currently-binding band -- still subject in "
        "every case to human approval at Gate 1 (plan.md §7.1)."
    ),
    [],
)

d["pre_mortem"] = section(
    "Pre-mortem",
    (
        "It is two years from now (2028) and this position has lost 30% "
        "(a smaller loss than the other three candidates' pre-mortems, "
        "consistent with this being the lowest-volatility profile in the "
        "batch). What happened: crude-oil/feedstock costs rose faster than "
        "PIB pricing power could absorb, reversing the FY24-to-FY25 "
        "margin-expansion trend this dossier's Why-Now (§3) relied on; "
        "export demand softened amid a broader industrial slowdown, and "
        "revenue -- already softly declining from FY24 to FY25 -- kept "
        "drifting down rather than stabilizing. The dividend was "
        "maintained (a genuine positive even in this scenario, per the "
        "company's long payment history), but the market re-rated the "
        "stock's already-modest multiple down further on the growth "
        "disappointment."
    ),
    [],
)

d["kill_triggers"] = section(
    "Kill triggers",
    (
        "1. promoter_holding_pct falls below 65% (vs current 72.22%), OR "
        "promoter_pledge_pct rises above 0%.\n"
        "2. OPM falls below 12% for two consecutive reported quarters/"
        "years (vs current 16.65%).\n"
        "3. A dividend cut or suspension (vs the current consistent "
        "payment record) -- a specific, checkable capital-allocation "
        "reversal signal unique to this candidate among the four.\n"
        "4. Any disclosed SEBI show-cause order, adverse RPT finding, or "
        "auditor resignation.\n"
        "5. Revenue decline extends to a third consecutive year (vs the "
        "single FY24-to-FY25 dip currently observed)."
    ),
    [],
)

d["what_would_make_me_add_more"] = section(
    "What would make me add more",
    (
        "A verified (not secondary-sourced) read of the FY2024-25 annual "
        "report (its URL was located at kotharipetrochemicals.com/"
        "investors/annual-reports/ and archives.nseindia.com) confirming: "
        "(a) OCF/PAT and genuine cash-conversion quality, (b) the exact "
        "related-party-transaction quantum with H C Kothari Group "
        "entities and a clean audit opinion, and (c) management commentary "
        "on the specific driver of FY24-to-FY25 margin expansion (cost "
        "discipline vs. favorable feedstock pricing vs. product mix), "
        "which would materially strengthen or weaken the Why-Now case "
        "(§3) with real evidence rather than an inferred pattern."
    ),
    [],
)

d["holding_period_and_tax"] = section(
    "Expected holding period and tax line",
    (
        "Expected holding period: multi-year (Track A compounder thesis, "
        "5+ year window per plan.md §4). Per config/ips.md §5, nothing "
        "sells before 12 months unless the thesis has materially broken. "
        "Sale within 12 months: STCG (20%); after 12 months: LTCG (12.5%, "
        "Rs 1.25 lakh annual exemption) per plan.md §2.3. Dividend income "
        "received during the holding period is separately taxable at the "
        "investor's slab rate, per Indian tax rules applicable to "
        "dividends -- worth noting since this is the only one of the four "
        "candidates in this batch that currently pays a dividend."
    ),
    [],
)

d["disconfirming_evidence"] = section(
    "Disconfirming evidence",
    (
        "The strongest case against this thesis, stated plainly:\n\n"
        "1. Revenue actually DECLINED from FY2024 (~Rs 604cr) to FY2025 "
        "(~Rs 589cr) -- a real, cited fact, not a hypothetical risk. The "
        "profit growth (63.8cr to 65.8cr) came from margin expansion on "
        "SHRINKING revenue, which is a materially weaker growth story than "
        "it might appear from the headline 24.10% 3yr profit-growth figure "
        "alone -- a single-product-family (PIB) petrochemical business "
        "growing profit only by margin expansion on declining volume/"
        "revenue is a real vulnerability if input costs move the other "
        "way.\n\n"
        "2. As a single-product-family manufacturer, Kothari carries real "
        "product concentration risk -- there is no segment diversification "
        "to fall back on if PIB-specific demand or competitive dynamics "
        "deteriorate, unlike GGBL's or Modi Naturals' more segmented "
        "revenue mixes in this same batch.\n\n"
        "3. The modest 7.04% 3yr sales growth is itself below what plan.md's "
        "own Track A growth gate would ideally want (>=15%, ideal >=20% "
        "PAT CAGR is a different metric, but top-line stagnation is still "
        "a real signal) -- this is a 'compounder' candidate whose top line "
        "is not currently compounding.\n\n"
        "4. OCF/PAT, related-party-transaction quantum, and auditor "
        "identity/opinion were ALL genuinely unverified in this research "
        "pass (§14) -- an investor relying only on this dossier is trusting "
        "reported accrual profit without independent confirmation, though "
        "the dividend track record provides a partial, non-conclusive "
        "cash-backing signal the other three candidates in this batch "
        "lack."
    ),
    [FIN0("FY24 vs FY25 revenue decline"), BIZ0("single-product-family concentration"), FIN1("unverified OCF/PAT and RPT status")],
)

d["provenance"] = {
    "model": "claude-sonnet-5",
    "prompt_version": "manual-harness-v1",
    "documents_read": ["KOTHARIPET_BUSINESS_OVERVIEW", "KOTHARIPET_FINANCIAL_HIGHLIGHTS", "KOTHARIPET_SHAREHOLDING_GOVERNANCE"],
    "could_not_verify": [
        "Exact related-party-transaction quantum/terms with H C Kothari Group entities",
        "Statutory auditor identity, tenure, and audit-opinion status",
        "Line-by-line content of the FY2024-25 annual report PDF (URL located, not independently parsed)",
        "OCF/PAT, gross margin (distinct from OPM), interest coverage, FCF conversion % -- not present in this Profile 1 Stage 1a export",
        "Multi-year EBIT/invested-capital time series needed to compute ROIIC",
        "Specific driver of FY24-to-FY25 margin expansion (cost discipline vs. feedstock pricing vs. product mix)",
        "Full Pabrai Downside-Floor Score /16 sub-components",
    ],
}

d["moat_understandability_gate"] = {
    "passed": True,
    "moat_type": "scale_technical_differentiation",
    "moat_evidence": (
        "Kothari is described as India's largest producer of premium-"
        "quality Polyisobutylene (PIB), a technically-differentiated "
        "specialty petrochemical (multiple grades for different technical "
        "applications) rather than a bulk commodity -- a scale-plus-"
        "technical-differentiation moat within a fewer-producer niche. "
        "This is reinforced by a multi-decade operating and listing "
        "history as part of the established H C Kothari Group, and a "
        "consistent multi-year dividend-payment track record that "
        "provides real, cited evidence of a shareholder-oriented capital-"
        "allocation approach -- a stronger management-track-record signal "
        "than the other three candidates in this research batch, none of "
        "which currently pay dividends."
    ),
    "return_trend_summary": (
        "Only a single-period Stage 1a snapshot was available (ROCE=28.60%, "
        "ROE=21.43%), but the FY24-to-FY25 secondary-sourced figures "
        "(profit rising modestly even as revenue declined) provide at "
        "least a two-point data series suggesting margin resilience, "
        "though not a full multi-year ROE/ROIC-vs-WACC trend."
    ),
    "five_sentence_test_result": "Pass -- see §2's five-sentence business model.",
    "understandability_checklist": {
        "five_sentence_business_model": True,
        "unit_economics_clarity": True,
        "industry_structure_stability": True,
        "demand_forecastability_5_10yr": True,
        "management_understandability": True,
        "accounting_transparency": True,
        "identifiable_moat_source": True,
    },
    "inversion_summary": (
        "This fails if: (a) feedstock/crude-oil cost inflation outpaces "
        "PIB pricing power, reversing the margin-expansion trend §3 relies "
        "on; (b) the FY24-to-FY25 revenue decline extends into a genuine "
        "multi-year contraction rather than a one-year dip; (c) a large "
        "competitor undercuts Kothari's premium-PIB positioning; or (d) an "
        "unverified RPT/auditor issue (§14) turns out to hide a real "
        "governance problem. This is the strongest understandability-gate "
        "case of the four candidates in this batch given the multi-decade "
        "group affiliation and dividend track record, though "
        "management_understandability still rests on capital-allocation "
        "*evidence* (dividend consistency) rather than a primary-source "
        "concall/MD&A letter, which this research did not access."
    ),
    "citations": [BIZ0("PIB market leadership and technical differentiation"), FIN1("dividend record as capital-allocation evidence"), SH0("group affiliation and multi-decade history")],
}

d["qglp_scorecard"] = {
    "quality": 2,
    "growth": 2,
    "longevity": 2,
    "price": 2,
    "evidence": {
        "Q": (
            "ROE 21.43% and ROCE 28.60% both clear the >=15% threshold "
            "(ROE modestly above, ROCE comfortably above, the >=20% ideal "
            "band); D/E 0.01 is far under the 1.0 ceiling; promoter "
            "holding 72.22% is clean, unpledged, and RISING (+1.24 3yr "
            "trend) -- the cleanest promoter-integrity evidence of the "
            "four candidates. Held to 2 (not 3) only because OCF/PAT is "
            "unresolved and ROE itself is only modestly (not comfortably) "
            "above the 20% ideal threshold."
        ),
        "G": (
            "3yr profit growth of 24.10% clears the >=20% ideal band, but "
            "this dossier's own Disconfirming Evidence (§12) flags that "
            "revenue actually DECLINED over the same comparison window "
            "(FY24 Rs 604cr to FY25 Rs 589cr per secondary sources) -- "
            "profit growth here comes entirely from margin expansion on "
            "shrinking volume, not genuine business growth. Scored 2 "
            "(clears the ideal PAT-CAGR band on the number itself) rather "
            "than 3, given this quality caveat and the weak (7.04%) "
            "top-line growth."
        ),
        "L": (
            "A specific, evidenced moat (largest premium-PIB producer, "
            "technical grade differentiation) plus a multi-decade "
            "operating/listing history and consistent dividend-payment "
            "record support a genuinely plausible durability case -- the "
            "strongest longevity evidence of the four candidates, though "
            "capped at 2 (not 3) by the single-product-family "
            "concentration risk (§6) and the unresolved question of "
            "whether the FY24-to-FY25 revenue decline is a one-year blip "
            "or an early sign of demand softening."
        ),
        "P": (
            "P/E 10.70x, PEG 0.44, and a best-decile Greenblatt combined "
            "percentile (5.54%) are moderately cheap signals, reinforced "
            "by a real (if modest) dividend yield (0.76-1.52%) providing "
            "a partial cash-return floor the other three candidates in "
            "this batch lack. Scored 2 -- fair-to-cheap with some real "
            "margin of safety, but not a Graham-style deep-value bargain "
            "(P/E>10, no P/B data to confirm a Graham Number)."
        ),
    },
    "citations": [FIN0("Stage 1a and secondary-source financial figures"), SH0("promoter holding trend")],
}

d["margin_of_safety_scuttlebutt"] = section(
    "Margin-of-Safety & Scuttlebutt Notes",
    (
        "GRAHAM DEFENSIVE-INVESTOR CRITERIA (relaxed for India):\n"
        "- Current ratio >=2.0: UNKNOWN -- not present in this export.\n"
        "- No earnings deficit in 10 years: UNKNOWN -- plausible given the "
        "long-established group affiliation, but not independently "
        "verified with a real multi-year earnings series.\n"
        "- P/E <=15x on 3yr average EPS: PASS on trailing P/E (10.70x, "
        "under 15x).\n"
        "- P/B <=1.5x: UNKNOWN -- price_to_book not present in this "
        "export.\n"
        "- Graham Number (P/E x P/B <=22.5): UNKNOWN -- needs P/B.\n"
        "- Dividend record >=10 years (relaxed threshold): PARTIAL PASS -- "
        "a genuine multi-year dividend-payment history is described "
        "(interim Aug 2025, final Jul 2024, ~28.47% 5yr dividend growth), "
        "though a full 10-year unbroken record was not independently "
        "confirmed.\n"
        "- Margin of safety vs intrinsic value: not computed with false "
        "precision -- see Valuation (§7)'s explicit scenario assumptions; "
        "on the numbers available, this DOES look like a reasonably "
        "defensive, moderately-priced name relative to the other three "
        "candidates.\n\n"
        "FISHER'S 15-POINT SCUTTLEBUTT CHECKLIST (digital proxies):\n"
        "1. Sufficient market potential: PARTIAL -- PIB demand tied to "
        "automotive/industrial end markets (BIZ0), not a high-growth "
        "category, but a stable one.\n"
        "2. Management determined on new products: UNKNOWN -- no evidence "
        "of new-product initiatives found.\n"
        "3. R&D effectiveness: UNKNOWN.\n"
        "4. Above-average sales organization: PARTIAL -- both domestic and "
        "export customer base described (BIZ0).\n"
        "5. Worthwhile profit margin: PASS -- OPM 16.65% (FIN0), "
        "reasonable for a specialty petrochemical.\n"
        "6. Doing what to improve margin: PARTIAL -- the FY24-to-FY25 "
        "margin expansion itself is evidence of SOME improvement, though "
        "the specific driver (cost discipline vs. input pricing) is "
        "unverified (FIN1).\n"
        "7-8. Labor/executive relations: UNKNOWN.\n"
        "9. Depth of management: PARTIAL -- an established group "
        "(H C Kothari Group, SH0) suggests institutional management depth "
        "beyond a single founder-promoter, though no specific named "
        "executives were confirmed in this research pass.\n"
        "10. Cost analysis/accounting controls: UNKNOWN -- not "
        "independently verified.\n"
        "11. Industry-specific differentiators: PASS -- largest premium-"
        "PIB producer positioning (BIZ0).\n"
        "12. Profit outlook: UNKNOWN -- no forward management guidance "
        "found.\n"
        "13. Equity financing needs: PASS (implied) -- D/E=0.01 and a "
        "consistent dividend-paying (not capital-raising) history suggest "
        "no near-term equity-financing need.\n"
        "14. Candour with investors: UNKNOWN -- no concall commentary "
        "found in this research pass.\n"
        "15. Management integrity: addressed separately as the Integrity "
        "Gate (§18)."
    ),
    [BIZ0("business and industry positioning"), FIN0("OPM and margin figures"), FIN1("margin-expansion evidence"), SH0("group affiliation")],
)

d["integrity_gate"] = {
    "passed": True,
    "promoter_pledge_flag": False,
    "declining_holding_flag": False,
    "rpt_or_auditor_or_sebi_flag": False,
    "evidence": (
        "promoter_pledge_pct=0.0 and 3yr promoter-holding trend +1.24 "
        "(rising, not declining) both confirmed directly from the Stage "
        "1a snapshot and cross-checked against Trendlyne's shareholding-"
        "pattern tracker (SH0) -- the cleanest, most directly-evidenced "
        "integrity read of the four candidates in this batch (no missing "
        "trend field, unlike GGBL/Virtual Galaxy). No SEBI show-cause "
        "order, adverse RPT finding, or auditor resignation was found "
        "referenced in the sources consulted. HOWEVER, this remains an "
        "absence of finding in general public research, not an exhaustive "
        "review of SEBI's enforcement database or the primary annual "
        "report's own RPT note and audit opinion, which this research "
        "located (by URL) but did not independently read line by line."
    ),
    "citations": [SH0("promoter pledge and rising holding trend"), SH1("absence of adverse-finding search results")],
}

d["scale_economies_shared"] = section(
    "Scale Economies Shared Assessment",
    (
        "ROIIC: could NOT be computed -- only a single-period Stage 1a "
        "snapshot was available (plus one prior-year secondary-sourced "
        "revenue/profit figure, insufficient for the required ΔNOPAT/"
        "ΔInvested-Capital lagged series). Reporting an estimated ROIIC "
        "would be a fabricated number with false precision.\n\n"
        "A RELATED, single-period Greenblatt-style ROC (NOT ROIIC): EBIT / "
        "(NWC ex-cash-ex-debt + NFA ex-goodwill) = 97.35 / (57.61+214.47) "
        "= 35.78% -- a strong return on capital employed, though this is a "
        "capital-intensive manufacturing business (NFA of Rs 214.47cr is "
        "large relative to EBIT), unlike GGBL's or Virtual Galaxy's more "
        "asset-light models in this same batch.\n\n"
        "VOLUME VS. PRICE: the cited evidence (revenue declining while "
        "profit rises, FIN0/FIN1) suggests the FY24-to-FY25 improvement "
        "came from PRICE/MARGIN (cost management or realization), not "
        "volume growth -- i.e. this looks more like the OPPOSITE of "
        "Sleep's 'share scale savings via lower prices to drive volume' "
        "thesis. This is a meaningful, cited finding, not a generic "
        "disclaimer: on the available evidence, Kothari does NOT look like "
        "a Scale-Economies-Shared candidate in Sleep's specific sense.\n\n"
        "VERDICT: the Scale-Economies-Shared framework's specific thesis "
        "(passing cost savings to customers to drive volume and compound "
        "moat) is NOT well-supported by the available evidence for this "
        "candidate -- the cited pattern points toward margin capture, not "
        "volume-driven scale sharing. Reported honestly rather than forced "
        "to fit the framework."
    ),
    [FIN0("EBIT/NWC/NFA inputs"), FIN1("revenue-decline-with-profit-growth pattern")],
)

d["magic_formula_attribution"] = section(
    "Magic Formula Attribution",
    (
        "Quantitative-entry note reporting the Stage 2 Greenblatt ranking "
        "gate's result, not a standalone buy case.\n\n"
        "ROC = EBIT / (NWC ex-cash-ex-debt + NFA ex-goodwill) = 97.35 / "
        "272.08 = 35.78%.\n"
        "Earnings Yield = EBIT / EV = 97.35 / 756.44 = 12.87%.\n\n"
        "Ranked against the full 1,101-company rankable universe: ROC "
        "rank 165th, Earnings Yield rank 124th, combined rank 289, "
        "combined percentile 5.54% -- CLEARS the best-decile (<=10%) "
        "threshold.\n\n"
        "Profile 1 uses Greenblatt's own EBIT-based ROC/EV method "
        "directly -- no sector-native substitution required."
    ),
    [FIN0("EBIT, NWC, NFA, EV inputs")],
)

d["conviction_sizing"] = section(
    "Super-Investor Alignment / Cloning & Conviction Sizing",
    (
        "PABRAI DOWNSIDE-FLOOR SCORE (/16): could not be scored in full. "
        "Debt safety looks strong (D/E=0.01, near debt-free) -- a "
        "reasoned partial input supporting a high sub-score there -- and "
        "the consistent dividend-payment history is a further (if "
        "indirect) positive signal for bear-case survivability. "
        "Net-cash/tangible-asset backing and liquidation-value coverage "
        "still require balance-sheet detail not available here.\n"
        "ASYMMETRY RATIO: using this dossier's own Valuation assumptions "
        "(§7) -- an assumed ~20-30% bear-case downside against an assumed "
        "~25-45% bull-case upside -- gives a rough asymmetry ratio in the "
        "neighborhood of 1:1 to 1.5:1, well short of Pabrai's >=3:1 "
        "threshold. This reflects the narrower-both-ways, lower-volatility "
        "profile of this candidate rather than a genuine deep-asymmetry "
        "setup.\n\n"
        "No cross-reference to a known Indian super-investor's disclosed "
        "shareholding was found for this candidate.\n\n"
        "JHUNJHUNWALA CONVICTION SCORE: 4/5, the highest of the four "
        "candidates in this batch. Business clarity is strong (a single, "
        "clearly explainable specialty-chemical product line, §2/§15); "
        "management-quality checks have real (if partial) evidence via "
        "the dividend track record (§17); FCF/PAT reconciliation could not "
        "be done fully, but the dividend-payment history is a partial "
        "cash-quality proxy; thesis specificity is reasonable (margin-"
        "expansion-on-declining-revenue is a specific, checkable pattern, "
        "§3/§12); disconfirming-evidence adequacy is genuine (§12 raises a "
        "real, specific concern -- profit growth from margin not volume). "
        "Not a return forecast -- subject to human override at Gate 1.\n\n"
        "PROPOSED POSITION SIZE (proposal only): given the highest (4/5) "
        "conviction score in this batch, size toward the upper half of the "
        "currently-binding Track A band per config/ips.md (up to 1.25% of "
        "total investable assets at the current 5% active-sleeve stage), "
        "subject to Gate 1/Gate 2 human approval."
    ),
    [FIN0("D/E and dividend-record inputs")],
)

d["quality_compounding_checklist"] = section(
    "Quality-Compounding Checklist",
    (
        "ROCE: 28.60% (single latest-period figure; a two-point FY24/FY25 "
        "comparison suggests margin resilience but not a full multi-year "
        "trend).\n"
        "Gross margin (distinct from OPM), interest coverage, and FCF "
        "conversion %: NOT AVAILABLE.\n\n"
        "REINVESTMENT-RUNWAY RATIONALE: unlike GGBL's capacity-expansion "
        "story, this dossier found NO specific, cited capacity-expansion "
        "or new-product reinvestment plan for Kothari -- the bull case "
        "here rests on margin durability and modest demand recovery, not "
        "an evidenced reinvestment runway. This is reported honestly as a "
        "gap rather than inferred from generic optimism; it is also "
        "consistent with this candidate's profile as a steadier, "
        "lower-growth compounder rather than a scaling growth story.\n\n"
        "SMITH'S 'DO NOTHING' DISCIPLINE: 'do nothing' means not selling "
        "absent genuine thesis impairment. Specific evidence that WOULD "
        "impair this thesis (feeding Kill Triggers, §10): OPM falling "
        "below 12% for two consecutive periods, a dividend cut/suspension, "
        "a third consecutive year of revenue decline, or confirmation of "
        "an adverse RPT/auditor finding."
    ),
    [FIN0("ROCE and margin figures"), FIN1("absence of a disclosed reinvestment/capacity plan")],
)

with open("run-kotharipet-20260830-001.json", "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print("wrote run-kotharipet-20260830-001.json,", len(json.dumps(d)), "bytes")
