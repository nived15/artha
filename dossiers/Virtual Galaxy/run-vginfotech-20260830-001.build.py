"""Reproducibility artifact for dossiers/Virtual Galaxy/run-vginfotech-20260830-001.md.

Manually-orchestrated research pass (see dossiers/Eco Recyc/'s own
precedent note on the artha-dossier factory's placeholder assembly step).
Inputs: this script + filings/VGINFOTECH/*.txt (ingested via
`artha data import-filing`). Every citation was fetched via
get_filing_chunk/list_candidate_chunks before being written here. Track B
(asymmetric bet) -- includes davis_double_play and canslim_notes sections,
omits quality_compounding_checklist per the schema.
"""
import json

SNAPSHOT_ID = "a0d7e35e3abb34602e52ac01075992c76e302178919722d74cb3769f8ad75198"
RUN_ID = "run-vginfotech-20260830-001"
TICKER = "Virtual Galaxy"

def cit(doc_id, note, chunk_index=0):
    return {"doc_id": doc_id, "page": 1, "note": f"{note} (chunk_index={chunk_index})"}

BIZ0 = lambda n: cit("VGINFOTECH_BUSINESS_OVERVIEW", n, 0)
BIZ1 = lambda n: cit("VGINFOTECH_BUSINESS_OVERVIEW", n, 1)
FIN0 = lambda n: cit("VGINFOTECH_FINANCIAL_HIGHLIGHTS", n, 0)
FIN1 = lambda n: cit("VGINFOTECH_FINANCIAL_HIGHLIGHTS", n, 1)
SH0 = lambda n: cit("VGINFOTECH_SHAREHOLDING_GOVERNANCE", n, 0)
SH1 = lambda n: cit("VGINFOTECH_SHAREHOLDING_GOVERNANCE", n, 1)

def section(title, content, citations=None):
    return {"title": title, "content": content, "citations": citations or []}

d = {}

d["identity"] = {
    "company": "Virtual Galaxy Infotech Limited",
    "ticker": TICKER,
    "sector": "Software Products",
    "arithmetic_profile": "profile_1_standard",
    "track": "B",
    "date": "2026-08-30",
    "pipeline_run_id": RUN_ID,
    "snapshot_id": SNAPSHOT_ID,
}

d["business_five_sentences"] = section(
    "The business in five sentences",
    (
        "Virtual Galaxy Infotech Limited (VGIL) is a Nagpur-headquartered "
        "IT/enterprise-software company, founded in 1997, with roughly "
        "three decades of pre-listing operating history despite a recent "
        "stock-market listing. Its flagship product, 'E-Banker,' is a "
        "core-banking solution reportedly deployed across over 5,000 bank "
        "branches, alongside ERP systems, e-governance platforms "
        "(E-APMC, E-Autopsy), a tax-compliance product (VGST), a payments "
        "product (V-Pay), and cloud/cybersecurity services, serving BFSI, "
        "government, and industrial clients. IMPORTANT RISK FLAG: it is "
        "listed on the NSE SME (Emerge) platform, NOT the mainboard -- "
        "carrying materially lighter disclosure obligations, thinner "
        "liquidity, and a much shorter public-market track record than a "
        "mainboard listing. It is controlled by a single promoter group at "
        "65.00% holding, zero pledge, with the vast majority of promoter "
        "shares under a SEBI-mandated SME lock-in. Financially it screens "
        "very strongly (46.25% OPM, 33.74% ROCE, 8.01x P/E), but on a "
        "still-small absolute revenue base (~Rs 120cr FY2025)."
    ),
    [BIZ0("business description and core-banking product"), BIZ1("SME listing risk flag"), SH0("promoter holding and lock-in")],
)

d["why_now"] = section(
    "Why now",
    (
        "Two catalysts, both genuinely strong but both requiring the "
        "SME-listing caveat to be weighed alongside them: (1) Q4 FY2025-26 "
        "results show a sharp acceleration -- revenue ~Rs 55.44cr (up "
        "~190% YoY from ~Rs 19.06cr) and net profit ~Rs 14.49cr (up ~195% "
        "YoY from ~Rs 4.90cr), with net margin holding steady at ~26%. "
        "(2) The stock screens as one of the cheapest, best-quality names "
        "in this entire research batch on a combined basis: P/E 8.01x, "
        "PEG 0.04, OPM 46.25% (the highest of any candidate in this "
        "batch, consistent with a software/IP-licensing model rather than "
        "a hardware/EPC one), and a best-decile Greenblatt combined "
        "percentile (7.27%, see §21). HOWEVER, the ~190% YoY growth is "
        "measured off a genuinely small base (~Rs 19-55cr per quarter), "
        "and the SME listing means this quarter-over-quarter acceleration "
        "carries less independent verification than an equivalent "
        "mainboard disclosure would."
    ),
    [FIN0("Q4 FY2025-26 acceleration"), BIZ1("SME listing risk")],
)

d["three_things_must_be_true"] = section(
    "The three things that must be true",
    (
        "1. The Q4 FY2025-26 growth acceleration (~190% YoY revenue, "
        "~195% YoY profit) must be confirmed as a durable multi-quarter "
        "trend, not a one-off tied to a single large contract -- "
        "falsifiable by a reversion toward the much smaller prior-year "
        "quarterly base in subsequent disclosures.\n"
        "2. The core-banking/e-governance software business must retain "
        "real switching-cost economics (once E-Banker is embedded in a "
        "bank's operations, it should be sticky) rather than facing "
        "displacement by larger players (Infosys Finacle, TCS BaNCS) "
        "moving down-market -- falsifiable by disclosed client losses or "
        "contract non-renewals.\n"
        "3. The promoter group's clean, unpledged 65.00% holding must "
        "continue past the SEBI SME lock-in period (i.e. once shares "
        "become freely sellable, holding must not decline sharply), with "
        "no adverse RPT/auditor/SEBI finding -- falsifiable by a promoter "
        "sell-down once lock-in expires, or any of the other specific "
        "events."
    ),
    [],
)

d["financial_evidence"] = section(
    "Financial evidence",
    (
        "From the ingested Stage 1a snapshot: Market Cap Rs 369.30cr; ROCE "
        "33.74%; ROE 29.58%; D/E 0.22; OPM 46.25% (highest of the four "
        "candidates in this batch); 3yr sales growth 46.38%; 3yr profit "
        "growth 194.74%; P/E 8.01x; Artha PEG 0.04; EBIT Rs 67.43cr; Net "
        "Working Capital (ex-cash/debt) Rs 48.91cr; Net Fixed Assets "
        "(ex-goodwill) Rs 192.59cr; Enterprise Value Rs 386.50cr; Promoter "
        "holding 65.00%, pledge 0.00%, 3yr trend not present in this "
        "export (null, not assumed flat).\n\n"
        "From secondary web research: FY2025 revenue ~Rs 120cr; 5yr profit "
        "CAGR ~83.8%; Q4 FY2025-26 revenue ~Rs 55.44cr (up ~190% YoY) vs "
        "Q4 FY2024-25 ~Rs 19.06cr; Q4 FY2025-26 net profit ~Rs 14.49cr "
        "(up ~195% YoY) vs ~Rs 4.90cr; net margin ~26% in both quarters "
        "(stable, at least).\n\n"
        "NOT AVAILABLE: OCF/PAT, gross margin (distinct from OPM), "
        "interest coverage, FCF conversion %, current ratio, price-to-"
        "book, dividend record (none paid), and any independent order-"
        "book or named-client disclosure."
    ),
    [FIN0("Stage 1a and secondary-source figures"), FIN1("growth-quality caveat on the small base")],
)

d["fatal_flaw_checklist"] = section(
    "Fatal-flaw checklist",
    (
        "- promoter_pledging: PASS (0.00%).\n"
        "- promoter_holding_not_declining: the numeric 3yr-trend field is "
        "absent from this export, but the shareholding-governance "
        "document's secondary research shows holding steady at 65.00% "
        "across all recent quarters (SH0) -- treated as sufficient "
        "corroborating evidence. NOTE: over 99.5% of promoter shares are "
        "under a SEBI-mandated SME-IPO lock-in (SH0) -- this stability is "
        "PARTLY a regulatory artifact (promoters cannot sell even if they "
        "wanted to), not purely a voluntary conviction signal, and should "
        "be re-tested once the lock-in expires.\n"
        "- profit_becomes_cash (OCF/PAT>=0.8): NEEDS_STAGE_1B -- not a "
        "field in this export.\n"
        "- survives_worst_year_without_dilution, price_assumption_"
        "plausible: NEEDS_STAGE_3.\n"
        "- no_single_point_of_failure_dependency: a real, unresolved "
        "concern -- no independent client-concentration or order-book "
        "disclosure was found (BIZ1), so this research CANNOT rule out "
        "that the Q4 FY2025-26 acceleration is concentrated in one or two "
        "large contracts (a common pattern for small enterprise-software "
        "vendors). This is explicitly reported as unresolved, not assumed "
        "diversified.\n"
        "- business_explainable_in_five_sentences: PASS, see §2.\n"
        "- no_serial_equity_dilution: NEEDS_STAGE_1B, though the IPO "
        "itself (raising ~Rs 93.3cr) is a known, recent capital-raising "
        "event worth noting as context, not a red flag by itself.\n"
        "- Greenblatt ranking gate: ROC = EBIT/(NWC+NFA) = 67.43/"
        "(48.91+192.59) = 27.92%; Earnings Yield = EBIT/EV = 67.43/386.50 "
        "= 17.45%. ROC rank 283/1101, EY rank 49/1101, combined rank 332, "
        "combined percentile 7.27% -- CLEARS the best-decile (<=10%) "
        "threshold.\n\n"
        "ADDITIONAL FLAG SPECIFIC TO THIS CANDIDATE: the NSE SME/Emerge "
        "listing venue itself (BIZ1) means continuous-disclosure "
        "obligations are lighter than mainboard requirements -- this is "
        "not a 'fatal flaw' in the disqualifying sense the checklist "
        "tests for, but it materially reduces the reliability of an "
        "'absence of finding' on every other item in this checklist "
        "relative to the other three (mainboard-listed) candidates in "
        "this batch."
    ),
    [SH0("promoter pledge, holding stability, and lock-in caveat"), BIZ1("SME disclosure regime and unresolved client-concentration"), FIN0("EBIT/NWC/NFA/EV inputs for Greenblatt")],
)

d["valuation"] = section(
    "Valuation",
    (
        "Current: Market Cap Rs 369.30cr, EV Rs 386.50cr, P/E 8.01x, PEG "
        "0.04 -- statistically very cheap, reinforced by the best-decile "
        "Greenblatt combined percentile (7.27%).\n\n"
        "PEG CAVEAT (same pattern flagged for Modi Naturals and GGBL in "
        "this batch): the 0.04 PEG is computed against the 194.74% 3yr "
        "profit-growth figure, which is itself measured off a small "
        "revenue base (~Rs 120cr FY2025) -- this should NOT be read as an "
        "extreme margin-of-safety signal at face value.\n\n"
        "Stated assumptions (mine, not company guidance):\n"
        "- BEAR CASE: the Q4 FY2025-26 acceleration proves concentrated in "
        "one or two contracts that do not renew (a real, unresolved risk "
        "given the unverified client-concentration question, §6); growth "
        "reverts toward the much smaller prior-year quarterly base; "
        "combined with the SME listing's thinner liquidity, any "
        "disappointment could produce an outsized price move given the "
        "small free float. Rough assumption-driven downside: 40-60% from "
        "current levels -- the widest bear-case range of the four "
        "candidates in this batch, reflecting the SME-listing liquidity "
        "risk compounding the business-concentration risk.\n"
        "- BASE CASE: growth decelerates from the ~190% YoY pace toward a "
        "still-strong but more moderate rate (assume 30-50%), OPM holds "
        "near current levels given the software/IP-licensing model's "
        "structural operating leverage. This implies meaningful further "
        "upside even without the most extreme growth assumptions.\n"
        "- BULL CASE: the core-banking/e-governance switching-cost moat "
        "(§15) proves real, the Q4 acceleration continues as genuine new-"
        "client/new-product momentum (not one-off), and the stock "
        "migrates from SME to mainboard listing (a real, disclosed "
        "pathway some SME companies pursue) -- bringing improved "
        "liquidity and institutional coverage that could itself drive a "
        "re-rating independent of fundamentals. This is the genuine "
        "Track B 2x-3x asymmetric-bet case, but it is also the most "
        "speculative bull case of the four candidates in this batch, "
        "resting on both a business-execution AND a listing-status "
        "catalyst.\n\n"
        "Overall read: the cheapest headline multiples of the four "
        "candidates, but also the highest-variance outcome distribution -- "
        "genuinely a Track B asymmetric bet, not a disguised compounder."
    ),
    [FIN0("valuation multiples"), FIN1("growth-quality caveat"), BIZ1("SME listing and migration-pathway context")],
)

d["buy_below_and_sizing"] = section(
    "Buy-below price and position size",
    (
        "Given the QGLP Price score of 2/3 (§16, cheap but PEG-distorted) "
        "and a Jhunjhunwala conviction score of 3/5 (§23), a buy-below "
        "discipline should demand a meaningful discount given the SME-"
        "listing liquidity risk specifically: proposed buy-below roughly "
        "20-25% below current levels -- the widest discount of the four "
        "candidates in this batch, reflecting the compounding of "
        "business-concentration risk (§6) and listing-venue risk (§6, "
        "§15) rather than fundamentals alone.\n\n"
        "Position size: config/ips.md caps a fully-sized Track B position "
        "at 1.25% of total investable assets, restricted further at the "
        "initial 5% active-sleeve stage. Given the elevated SME-listing-"
        "specific liquidity risk (which is NOT captured by the "
        "conviction score alone, since that score is about business/"
        "thesis quality, not tradability), this proposal recommends "
        "sizing at or below the Modi Naturals allocation despite the "
        "higher conviction score here -- a deliberate, explicit deviation "
        "from a pure conviction-score-driven sizing rule, flagged as a "
        "human-reviewable judgment call, subject to Gate 1/Gate 2 human "
        "approval (plan.md §7.1)."
    ),
    [],
)

d["pre_mortem"] = section(
    "Pre-mortem",
    (
        "It is two years from now (2028) and this position has lost 65% -- "
        "the largest loss among this batch's pre-mortems. What happened: "
        "the Q4 FY2025-26 acceleration turned out to be concentrated in a "
        "small number of large contracts (exactly the unresolved risk "
        "§6 flagged) that did not renew, and growth reverted sharply "
        "toward the much smaller prior-year quarterly base. Compounding "
        "the fundamental disappointment, the stock's SME-listing thin "
        "liquidity meant the price move on the way down was sharper and "
        "harder to exit than a mainboard-listed equivalent would have "
        "been -- and with the SEBI lock-in on 99.5% of promoter shares "
        "having since expired, a promoter sell-down (unverifiable in "
        "advance from this research) added further selling pressure just "
        "as the fundamental thesis was breaking."
    ),
    [],
)

d["kill_triggers"] = section(
    "Kill triggers",
    (
        "1. promoter_holding_pct falls below 55% (vs current 65.00%), OR "
        "promoter_pledge_pct rises above 0%, OR any disclosed promoter "
        "sell-down once the SME lock-in expires.\n"
        "2. Quarterly revenue reverts below Rs 25cr for two consecutive "
        "quarters (vs the Q4 FY2025-26 figure of ~Rs 55.44cr) -- directly "
        "testing whether the acceleration was concentrated/one-off.\n"
        "3. OPM falls below 30% for two consecutive periods (vs current "
        "46.25%).\n"
        "4. Any disclosed SEBI show-cause order, adverse RPT finding, or "
        "auditor resignation.\n"
        "5. FII holding continues declining toward 0% (already down from "
        "~5% to ~1.12%, §18) with no offsetting increase in DII or "
        "mainboard-migration news -- a proxy for continued thin "
        "institutional validation."
    ),
    [],
)

d["what_would_make_me_add_more"] = section(
    "What would make me add more",
    (
        "A disclosed client list, order book, or contract-concentration "
        "breakdown confirming the Q4 FY2025-26 acceleration is broad-"
        "based (multiple clients/contracts) rather than concentrated in "
        "one or two large deals -- this is the single most decision-"
        "relevant missing piece of evidence for this candidate. "
        "Additionally: confirmation of continued growth in at least one "
        "further quarter, a verified (not secondary-sourced) read of the "
        "annual report/DRHP for OCF/PAT and RPT/auditor status, and any "
        "disclosed intent or progress toward mainboard migration (which "
        "would directly address the SME-listing liquidity/disclosure "
        "concern that is this candidate's single largest structural risk)."
    ),
    [],
)

d["holding_period_and_tax"] = section(
    "Expected holding period and tax line",
    (
        "Expected holding period: 2-3 years (Track B asymmetric-bet "
        "thesis per plan.md §4), contingent on confirming the Q4 "
        "acceleration is durable and not contract-concentrated, and on "
        "monitoring promoter behavior once the SME lock-in expires. Per "
        "config/ips.md §5, nothing sells before 12 months unless the "
        "thesis has materially broken. Sale within 12 months: STCG (20%); "
        "after 12 months: LTCG (12.5%, Rs 1.25 lakh annual exemption) per "
        "plan.md §2.3. NOTE: SME-platform stocks can have wider bid-ask "
        "spreads and thinner daily volume than mainboard names, which is "
        "a real execution-cost consideration at both entry and exit, "
        "distinct from the tax treatment itself."
    ),
    [],
)

d["disconfirming_evidence"] = section(
    "Disconfirming evidence",
    (
        "The strongest case against this thesis, stated plainly:\n\n"
        "1. This is an NSE SME (Emerge)-listed stock, NOT a mainboard "
        "listing -- lighter continuous-disclosure obligations, thinner "
        "liquidity, and a much shorter public-market track record than "
        "the other three candidates in this batch. Every 'absence of "
        "finding' in this dossier's governance/integrity research (RPT, "
        "auditor, SEBI) is a weaker signal here than for a mainboard-"
        "listed peer, because there is simply less public secondary-"
        "source scrutiny of SME companies.\n\n"
        "2. No independent client list, order book, or contract-"
        "concentration disclosure was found (§6) -- the Q4 FY2025-26 "
        "growth acceleration (~190% YoY) could plausibly be driven by one "
        "or two large deals rather than broad-based demand, and this "
        "research cannot rule that out.\n\n"
        "3. FII institutional holding has been DECLINING (from ~5% to "
        "~1.12%, §18) even as the headline growth numbers have "
        "accelerated -- an inconsistency worth taking seriously rather "
        "than dismissing, since it could reflect informed investors "
        "reducing exposure for reasons this research could not identify.\n\n"
        "4. Over 99.5% of promoter shares are under a SEBI-mandated "
        "lock-in (§18) -- the current shareholding stability is partly a "
        "regulatory artifact, not fully a voluntary conviction signal, "
        "and should be re-tested once that lock-in expires.\n\n"
        "5. OCF/PAT, related-party-transaction quantum, auditor identity/"
        "opinion, and the underlying driver of the Q4 acceleration were "
        "ALL genuinely unverified in this research pass (§14) -- an "
        "investor relying only on this dossier is trusting a single "
        "recent quarter's numbers from a thinly-covered SME stock without "
        "independent confirmation of any of these items."
    ),
    [BIZ1("SME listing risk and disclosure-regime caveat"), SH0("SME lock-in caveat"), SH1("declining FII holding")],
)

d["provenance"] = {
    "model": "claude-sonnet-5",
    "prompt_version": "manual-harness-v1",
    "documents_read": ["VGINFOTECH_BUSINESS_OVERVIEW", "VGINFOTECH_FINANCIAL_HIGHLIGHTS", "VGINFOTECH_SHAREHOLDING_GOVERNANCE"],
    "could_not_verify": [
        "Client list, order book, or contract-concentration breakdown behind the Q4 FY2025-26 acceleration",
        "Exact related-party-transaction quantum/terms",
        "Statutory auditor identity, tenure, and audit-opinion status",
        "Whether the declining FII holding trend reflects routine churn or reduced institutional conviction",
        "OCF/PAT, gross margin (distinct from OPM), interest coverage, FCF conversion % -- not present in this Profile 1 Stage 1a export",
        "Own 5-year P/E percentile and sector-median P/E (Davis Double Play's Stage 1b inputs)",
        "3yr promoter-holding trend field (absent from this export; secondary-source quarterly stability used as a partial substitute)",
        "Any disclosed intent or progress toward mainboard migration",
    ],
}

d["moat_understandability_gate"] = {
    "passed": True,
    "moat_type": "switching_cost_niche",
    "moat_evidence": (
        "VGIL's flagship 'E-Banker' core-banking software, reportedly "
        "deployed across over 5,000 bank branches, is the kind of product "
        "that -- IF the deployment figure is accurate -- carries genuine "
        "switching costs once embedded in a bank's core operations "
        "(migration risk, staff retraining, data-integrity risk all "
        "discourage a bank from switching core-banking vendors casually). "
        "This is a plausible, specific, named moat source (switching "
        "costs in enterprise software), not a generic 'strong brand' "
        "assertion -- but it rests on an unverified secondary-source "
        "client-count claim, not an independently confirmed client list "
        "(§6), which materially tempers confidence relative to a "
        "primary-source-verified moat."
    ),
    "return_trend_summary": (
        "Only a single-period Stage 1a snapshot plus one YoY quarterly "
        "comparison were available (ROCE=33.74%, ROE=29.58%, Q4 YoY "
        "revenue/profit both up ~190-195%) -- a full multi-year ROE/ROIC-"
        "vs-WACC trend could not be established, and the available "
        "evidence, while directionally positive, is thin (one quarter's "
        "YoY comparison)."
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
        "This fails if: (a) the Q4 acceleration proves concentrated in "
        "one or two large contracts that do not renew, exposing the "
        "growth as non-durable; (b) larger core-banking vendors (Infosys "
        "Finacle, TCS BaNCS, FIS, Oracle FLEXCUBE) move down-market and "
        "displace VGIL's smaller-bank/cooperative-bank niche; (c) the "
        "declining FII holding trend (§18) turns out to have reflected "
        "genuine informed-investor concern rather than routine churn; or "
        "(d) an unverified RPT/auditor issue (§14) turns out to hide a "
        "real governance problem, which is HARDER to rule out here than "
        "for the three mainboard-listed candidates in this batch given "
        "the SME platform's lighter disclosure regime. This is the "
        "LOWEST-CONFIDENCE gate pass of the four candidates in this "
        "batch specifically on accounting_transparency and "
        "identifiable_moat_source -- a stricter reader could reasonably "
        "fail this gate given the SME listing and the unverified client-"
        "count claim, and that judgment call is recorded honestly here, "
        "not smoothed over. This candidate should be monitored more "
        "closely post-purchase than the other three."
    ),
    "citations": [BIZ0("core-banking product and claimed deployment scale"), BIZ1("SME listing and competitive-landscape caveats"), SH1("declining FII holding")],
}

d["qglp_scorecard"] = {
    "quality": 2,
    "growth": 1,
    "longevity": 2,
    "price": 2,
    "evidence": {
        "Q": (
            "ROE 29.58% and ROCE 33.74% both clear the >=20% ideal "
            "threshold comfortably; D/E 0.22 is well under the 1.0 "
            "ceiling; promoter holding 65.00% is clean and unpledged, "
            "though the 3yr trend field is absent and the stability shown "
            "is partly a SEBI lock-in artifact (§6/§18) rather than pure "
            "voluntary conviction. Scored 2, capped by the unresolved "
            "OCF/PAT gap and the lock-in caveat."
        ),
        "G": (
            "3yr profit growth of 194.74% and the Q4 FY2025-26 ~195% YoY "
            "figure are both very high, but measured off a small absolute "
            "base (~Rs 120cr FY2025 revenue, ~Rs 19-55cr per quarter) -- "
            "the same low-base-effect concern flagged for GGBL and Modi "
            "Naturals in this batch. Scored 1, given the unverified "
            "multi-quarter consistency and the unresolved client-"
            "concentration question (§6) that could make even the recent "
            "acceleration non-durable."
        ),
        "L": (
            "A specific, named, plausible moat (core-banking-software "
            "switching costs, 29 years of pre-listing operating history) "
            "supports a genuine durability case -- the STRONGEST longevity "
            "argument of the two Track B candidates in this batch, given "
            "the switching-cost logic (stronger than Modi Naturals' "
            "brand-niche argument in a low-switching-cost food category). "
            "Scored 2 rather than 3 because the claimed 5,000+ bank-"
            "branch deployment is unverified beyond a secondary source, "
            "and the SME listing's thinner disclosure regime (§6) means "
            "this cannot be independently corroborated."
        ),
        "P": (
            "P/E 8.01x and PEG 0.04 look very cheap, and OPM 46.25% is "
            "the highest of any candidate in this batch -- but as with "
            "Modi Naturals and GGBL, the PEG is distorted by the same "
            "base-effect growth figure criticized in G above. Scored 2 "
            "(fair-to-cheap on the raw numbers, and the high OPM is a "
            "genuine, less-disputable positive) rather than 3, given the "
            "PEG-distortion caveat and the SME-listing liquidity risk "
            "that could itself explain part of the low multiple."
        ),
    },
    "citations": [FIN0("Stage 1a and secondary-source figures"), BIZ0("core-banking deployment claim")],
}

d["margin_of_safety_scuttlebutt"] = section(
    "Margin-of-Safety & Scuttlebutt Notes",
    (
        "GRAHAM DEFENSIVE-INVESTOR CRITERIA (relaxed for India; NOTE: "
        "several of these criteria, e.g. a 10-year record, are close to "
        "structurally inapplicable for a recent SME listing regardless of "
        "the underlying company's pre-listing operating age):\n"
        "- Current ratio >=2.0: UNKNOWN -- not present in this export.\n"
        "- No earnings deficit in 10 years: UNKNOWN -- and likely "
        "unanswerable from public markets data alone given the recent "
        "SME listing, even though the underlying business is ~29 years "
        "old (BIZ0).\n"
        "- P/E <=15x on 3yr average EPS: PASS on trailing P/E (8.01x).\n"
        "- P/B <=1.5x: UNKNOWN -- not present.\n"
        "- Graham Number: UNKNOWN -- needs P/B.\n"
        "- Dividend record: FAIL/NOT APPLICABLE -- no dividend paid.\n"
        "- Margin of safety: NOT computed with false precision given the "
        "PEG-distortion caveat (§7).\n\n"
        "FISHER'S 15-POINT SCUTTLEBUTT CHECKLIST (digital proxies):\n"
        "1. Sufficient market potential: PASS -- core-banking/e-"
        "governance software for India's large, still-digitizing BFSI and "
        "government sector (BIZ0).\n"
        "2. Management determined on new products: PASS -- a broad, "
        "actively-expanding product suite (E-Banker, ERP, e-governance, "
        "VGST, V-Pay, cloud/cybersecurity/conversational-AI, BIZ0) is "
        "itself evidence of continued product investment.\n"
        "3. R&D effectiveness: UNKNOWN -- no patent/R&D-spend evidence "
        "found.\n"
        "4. Above-average sales organization: PARTIAL -- the claimed "
        "5,000+ bank-branch deployment (BIZ0) is suggestive but "
        "unverified.\n"
        "5. Worthwhile profit margin: PASS -- OPM 46.25% (FIN0), the "
        "highest of any candidate in this batch.\n"
        "6. Doing what to improve margin: UNKNOWN -- no specific "
        "commentary found.\n"
        "7-8. Labor/executive relations: UNKNOWN.\n"
        "9. Depth of management: PARTIAL -- named CEO (Sachin Pande) and "
        "CFO (Avinash Shende) were identified in secondary research, "
        "though not cited in the ingested filing documents for this "
        "dossier and therefore not formally citable here -- reported as "
        "an uncited, unconfirmed data point rather than presented as a "
        "verified fact.\n"
        "10. Cost analysis/accounting controls: UNKNOWN -- and harder to "
        "verify than for the mainboard candidates given the SME "
        "disclosure regime (BIZ1).\n"
        "11. Industry-specific differentiators: PARTIAL -- core-banking "
        "switching-cost logic (BIZ0), tempered by no verified competitor/"
        "client comparison (BIZ1).\n"
        "12. Profit outlook: UNKNOWN -- no forward guidance found.\n"
        "13. Equity financing needs: PARTIAL -- the recent SME IPO (~Rs "
        "93.3cr raised) already addressed near-term capital needs; D/E of "
        "0.22 suggests low current reliance on debt.\n"
        "14. Candour with investors: UNKNOWN -- SME-listed companies "
        "generally have fewer analyst-covered concalls; none were found "
        "in this research pass.\n"
        "15. Management integrity: addressed separately as the Integrity "
        "Gate (§18)."
    ),
    [BIZ0("product suite and deployment claims"), BIZ1("SME disclosure regime"), FIN0("OPM")],
)

d["integrity_gate"] = {
    "passed": True,
    "promoter_pledge_flag": False,
    "declining_holding_flag": False,
    "rpt_or_auditor_or_sebi_flag": False,
    "evidence": (
        "promoter_pledge_pct=0.0 confirmed directly from the Stage 1a "
        "snapshot. The 3yr promoter-holding-trend field is absent, but "
        "secondary research shows holding steady at 65.00% across all "
        "recent quarters (SH0) -- though this stability is PARTLY a "
        "SEBI-mandated SME lock-in artifact (over 99.5% of promoter "
        "shares locked in) rather than purely voluntary, a caveat this "
        "gate records explicitly rather than treating the stability as "
        "unqualified good news. No SEBI show-cause order, adverse RPT "
        "finding, or auditor resignation was found referenced in the "
        "sources consulted. HOWEVER, given the SME platform's lighter "
        "disclosure regime (§6), this absence-of-finding is a WEAKER "
        "signal here than for the three mainboard-listed candidates in "
        "this batch -- 'not found' should be read as 'not yet "
        "independently verifiable from public secondary sources,' "
        "explicitly, not as 'confirmed clean.'"
    ),
    "citations": [SH0("promoter pledge, holding stability, and lock-in caveat"), SH1("SME disclosure-regime caveat on absence-of-finding reliability")],
}

d["davis_double_play"] = section(
    "The Davis Double Play Mechanism",
    (
        "Entry P/E: 8.01x (trailing). Own 5-year P/E percentile: UNKNOWN "
        "-- and likely unanswerable given VGIL's recent SME listing (a "
        "genuine 5-year own-history P/E series may not even exist yet as "
        "a listed company).\n"
        "Sector-median P/E (Software Products): UNKNOWN -- not computed "
        "as an aggregate over this screened universe in this research "
        "pass.\n"
        "Trailing EPS growth >=15%: the 3yr profit-growth figure "
        "(194.74%) and Q4 YoY figure (~195%) both clear this on their "
        "face, but per §6/§7/§12's repeated caveat, this is very likely a "
        "base-effect figure, not a clean confirmation of durable trailing "
        "growth.\n"
        "Reported acceleration (latest-quarter YoY AND TTM-vs-prior-TTM, "
        "both positive and improving): PARTIALLY supported -- the single "
        "Q4 FY2025-26 vs Q4 FY2024-25 comparison IS positive and a large "
        "improvement (~190-195% YoY), the clearest 'acceleration' evidence "
        "of the two Track B candidates in this batch, though it is only "
        "one quarter's data point, not a full TTM-vs-prior-TTM series "
        "(eps_growth_ttm_yoy is not present in this Profile 1 export).\n"
        "ROE >=15%: PASS (29.58%). D/E <=1.5x: PASS (0.22). P/E floor "
        ">=5x: PASS (8.01x).\n\n"
        "IMPLIED-RETURN FORMULA: (1 + trailing EPS CAGR)^3 x (sector-"
        "median P/E / entry P/E) - 1. Could NOT be computed with real "
        "inputs -- sector-median P/E is unavailable, and the trailing-"
        "growth figure is already flagged as base-effect-distorted. NOT "
        "computed rather than estimated with guessed inputs.\n\n"
        "OVERALL: of the two Track B candidates in this batch, Virtual "
        "Galaxy shows the STRONGER partial Davis-screen fit (a real, "
        "if single-quarter, reported-acceleration data point, plus clean "
        "ROE/D-E/PE-floor legs), but the two Stage-1b aggregate inputs "
        "(own 5yr P/E percentile, sector-median P/E) remain entirely "
        "unconfirmed for both candidates."
    ),
    [FIN0("Q4 acceleration and ROE/D-E inputs"), FIN1("base-effect caveat on the trailing growth figure")],
)

d["scale_economies_shared"] = section(
    "Scale Economies Shared Assessment",
    (
        "ROIIC: could NOT be computed -- only a single-period Stage 1a "
        "snapshot plus one YoY quarterly comparison were available; "
        "reporting an estimated ROIIC would be a fabricated number with "
        "false precision.\n\n"
        "A RELATED, single-period Greenblatt-style ROC (NOT ROIIC): EBIT / "
        "(NWC ex-cash-ex-debt + NFA ex-goodwill) = 67.43 / (48.91+192.59) "
        "= 27.92% -- a strong return on capital employed for a software "
        "business, though the NFA figure (Rs 192.59cr) is notably large "
        "relative to what a pure software/SaaS business might be expected "
        "to carry, which this research could not explain from available "
        "sources (possibly reflecting capitalized IP/product-development "
        "costs, but unverified).\n\n"
        "VOLUME VS. PRICE: no management quote distinguishing volume "
        "growth (more clients/deployments) from price increases was "
        "found. The claimed 5,000+ bank-branch deployment figure (BIZ0) "
        "is more consistent with a volume-driven growth story (more "
        "branches/clients using E-Banker) than a price-increase-driven "
        "one, but this is an inference, not a direct management quote, "
        "and the deployment figure itself is unverified.\n\n"
        "VERDICT: insufficient direct evidence for a confident moat-"
        "widening call on Sleep's specific volume-vs-price test, though "
        "the switching-cost moat argument (§15) is a related but distinct "
        "positive signal."
    ),
    [FIN0("EBIT/NWC/NFA inputs"), BIZ0("deployment scale as a volume-growth proxy")],
)

d["magic_formula_attribution"] = section(
    "Magic Formula Attribution",
    (
        "Quantitative-entry note reporting the Stage 2 Greenblatt ranking "
        "gate's result, not a standalone buy case.\n\n"
        "ROC = EBIT / (NWC ex-cash-ex-debt + NFA ex-goodwill) = 67.43 / "
        "241.50 = 27.92%.\n"
        "Earnings Yield = EBIT / EV = 67.43 / 386.50 = 17.45%.\n\n"
        "Ranked against the full 1,101-company rankable universe: ROC "
        "rank 283rd, Earnings Yield rank 49th, combined rank 332, "
        "combined percentile 7.27% -- CLEARS the best-decile (<=10%) "
        "threshold, driven substantially by the very strong earnings-"
        "yield rank (49th of 1101)."
    ),
    [FIN0("EBIT, NWC, NFA, EV inputs")],
)

d["conviction_sizing"] = section(
    "Super-Investor Alignment / Cloning & Conviction Sizing",
    (
        "PABRAI DOWNSIDE-FLOOR SCORE (/16): could not be scored in full. "
        "Debt safety looks strong (D/E=0.22) -- a reasoned partial input "
        "supporting a decent sub-score there -- but net-cash/tangible-"
        "asset backing, bear-case FCF survival, and liquidation-value "
        "coverage all require balance-sheet detail not available here, "
        "and are HARDER to obtain for an SME-listed company than for the "
        "three mainboard candidates in this batch.\n"
        "ASYMMETRY RATIO: using this dossier's own Valuation assumptions "
        "(§7) -- an assumed ~40-60% bear-case downside (the widest in "
        "this batch, reflecting compounded business + listing-venue risk) "
        "against an assumed 2x-3x bull-case upside -- gives a rough "
        "asymmetry ratio in the neighborhood of 1.7:1 to 3:1, at best only "
        "marginally clearing Pabrai's >=3:1 threshold at the optimistic "
        "end of the range. Built from this dossier's own scenario "
        "assumptions, not an independently verified calculation.\n\n"
        "No cross-reference to a known Indian super-investor's disclosed "
        "shareholding was found for this candidate.\n\n"
        "JHUNJHUNWALA CONVICTION SCORE: 3/5. Business clarity is "
        "reasonable (§2/§15, aided by the switching-cost moat argument); "
        "management-quality checks are thin and harder to verify given "
        "the SME disclosure regime (§17); FCF/PAT reconciliation could "
        "not be done; thesis specificity is reasonable (a specific "
        "quarterly acceleration figure, §3) but rests on an unconfirmed "
        "client-concentration question (§6); disconfirming-evidence "
        "adequacy is genuine and substantial (§12, five distinct concerns "
        "raised). Not a return forecast -- subject to human override at "
        "Gate 1.\n\n"
        "PROPOSED POSITION SIZE (proposal only): despite the moderate "
        "(3/5) conviction score, the SME-listing liquidity risk (§6, "
        "§8's own explicit deviation note) argues for sizing at or below "
        "Modi Naturals' allocation in this batch -- toward the LOW end of "
        "the currently-binding Track B band per config/ips.md, subject to "
        "Gate 1/Gate 2 human approval, and ideally deferred until a "
        "client-concentration or order-book disclosure is found."
    ),
    [FIN0("D/E input for debt-safety read")],
)

d["canslim_notes"] = section(
    "CANSLIM Momentum Screen Notes",
    (
        "Current-quarter EPS growth >=25% YoY: the Q4 FY2025-26 net-"
        "profit growth (~195% YoY) clears this decisively on its face -- "
        "the strongest CANSLIM fundamental-leg signal of the two Track B "
        "candidates in this batch -- though per repeated caveats above, "
        "this is measured off a small base and is a single quarter's data "
        "point.\n"
        "3-year EPS CAGR >=25% with ROE >=17%: 3yr profit growth "
        "(194.74%) and ROE (29.58%) both clear their thresholds "
        "comfortably on the numbers, with the same base-effect caveat.\n"
        "Price within 5% of a breakout pivot; breakout-day volume >=40% "
        "above 50-day average; constructed NSE/BSE relative-strength "
        "percentile >=80; Nifty 50/Sensex confirmed uptrend: ALL "
        "NEEDS_STAGE_3 -- no live price/volume/breadth market-data feed is "
        "wired up in this codebase yet (a Phase 5/6 item), and this would "
        "be doubly hard to construct reliably for a thinly-traded SME "
        "stock even once such a feed exists, given naturally lower "
        "trading volumes.\n\n"
        "OVERALL: the fundamental CANSLIM legs (current-quarter and "
        "3-year EPS growth, ROE) are the strongest of the two Track B "
        "candidates in this batch, but the technical/momentum "
        "confirmation layer is entirely unavailable, and would be "
        "structurally noisier to construct for an SME-listed name even "
        "once available -- reported honestly rather than assumed."
    ),
    [FIN0("Q4 YoY growth and ROE inputs")],
)

with open("run-vginfotech-20260830-001.json", "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print("wrote run-vginfotech-20260830-001.json,", len(json.dumps(d)), "bytes")
