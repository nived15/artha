"""Reproducibility artifact for dossiers/Ganesh Green/run-ggbl-20260830-001.md.

Manually-orchestrated research pass (matching dossiers/Eco Recyc/'s own
precedent -- the artha-dossier factory's assembly step is still a
placeholder per .github/extensions/artha-tools/extension.mjs). Inputs:
this script + filings/GGBL/*.txt (3 web-research-sourced documents,
ingested via `artha data import-filing`). Every citation below was
fetched via get_filing_chunk/list_candidate_chunks before being written
here -- see filings/GGBL/*.txt for the source text at each (doc_id, page,
chunk_index).
"""
import json

SNAPSHOT_ID = "a0d7e35e3abb34602e52ac01075992c76e302178919722d74cb3769f8ad75198"
RUN_ID = "run-ggbl-20260830-001"
TICKER = "Ganesh Green"

def cit(doc_id, note, chunk_index=0):
    return {"doc_id": doc_id, "page": 1, "note": f"{note} (chunk_index={chunk_index})"}

BIZ0 = lambda n: cit("GGBL_BUSINESS_OVERVIEW", n, 0)
BIZ1 = lambda n: cit("GGBL_BUSINESS_OVERVIEW", n, 1)
BIZ2 = lambda n: cit("GGBL_BUSINESS_OVERVIEW", n, 2)
FIN0 = lambda n: cit("GGBL_FINANCIAL_HIGHLIGHTS", n, 0)
FIN1 = lambda n: cit("GGBL_FINANCIAL_HIGHLIGHTS", n, 1)
SH0 = lambda n: cit("GGBL_SHAREHOLDING_GOVERNANCE", n, 0)
SH1 = lambda n: cit("GGBL_SHAREHOLDING_GOVERNANCE", n, 1)

def section(title, content, citations=None):
    return {"title": title, "content": content, "citations": citations or []}

d = {}

d["identity"] = {
    "company": "Ganesh Green Bharat Limited",
    "ticker": TICKER,
    "sector": "Other Electrical Equipment",
    "arithmetic_profile": "profile_1_standard",
    "track": "A",
    "date": "2026-08-30",
    "pipeline_run_id": RUN_ID,
    "snapshot_id": SNAPSHOT_ID,
}

d["business_five_sentences"] = section(
    "The business in five sentences",
    (
        "Ganesh Green Bharat Limited (GGBL) is an NSE-listed solar EPC "
        "(Engineering, Procurement, Construction) and photovoltaic-module "
        "manufacturing company, with an in-house automated module factory "
        "(1.1 GW capacity, stated plans to reach 2 GW by 2027). Its revenue "
        "mix spans solar EPC for government/industrial clients, PM-KUSUM "
        "solar water-pumping schemes, solar street lighting, lithium-ion "
        "cell manufacturing, electrical-contracting (transmission/"
        "distribution/substations), and Jal Jeevan Mission water-supply "
        "projects. It uses an asset-light EPC model: it owns project "
        "management/engineering/procurement capability and outsources "
        "labor-intensive execution to contract staff. Its stated "
        "differentiator is government-tender expertise and decentralized "
        "rural execution (e.g. solar water pumps) rather than head-to-head "
        "competition with the largest utility-scale EPC contractors. It is "
        "controlled by a single extended promoter family (the Patels), "
        "holding 73.42% with zero pledge."
    ),
    [BIZ0("solar EPC + module manufacturing business description"), SH0("promoter family identity and holding")],
)

d["why_now"] = section(
    "Why now",
    (
        "Two concrete, cited catalysts: (1) a large, forward-visible order "
        "book -- approximately Rs 2,212 crore as of FY26, described as "
        "nearly twice annual revenue -- gives near-term revenue visibility "
        "that a smaller, less-covered EPC name would not typically have "
        "disclosed this clearly. (2) A reported step-change in scale: FY26 "
        "revenue of approximately Rs 1,064 crore is described as roughly "
        "3x FY25, with PAT growing from ~Rs 30.22cr to ~Rs 75.18cr. BUT "
        "this 'why now' should be read with real caution: the underlying "
        "3-year Stage 1a growth figures (131.95% sales, 109.78% profit) "
        "describe growth off what still looks like a small base, and only "
        "a single secondary source was found for the FY26 vs FY25 "
        "comparison -- so this is a genuine window of rapid scaling, not "
        "an obviously mispriced multi-year-verified compounder."
    ),
    [FIN0("FY26 order book and revenue/PAT figures"), FIN1("growth-quality caveat on the small base")],
)

d["three_things_must_be_true"] = section(
    "The three things that must be true",
    (
        "1. The Rs 2,212cr order book must actually convert into revenue "
        "at a similar (not sharply lower) margin to the reported ~10.4-"
        "10.7% OPM/EBITDA margin -- falsifiable by a sustained margin "
        "decline or visible order-book-to-revenue conversion shortfall in "
        "future disclosures.\n"
        "2. India's solar-policy tailwind (domestic-manufacturing push, "
        "PM-KUSUM, rural electrification) must keep translating into new "
        "GGBL-won government tenders, not just the currently booked "
        "backlog -- falsifiable by several consecutive quarters with no "
        "new disclosed order wins, or a policy rollback.\n"
        "3. The promoter family (Patels, 73.42%, zero pledge) must keep "
        "its shareholding clean and stable, and no adverse RPT/auditor/"
        "SEBI finding may emerge -- falsifiable by any of those specific "
        "events; this is currently unverified beyond an absence-of-finding "
        "in secondary research (see Fatal-Flaw Checklist, Integrity Gate)."
    ),
    [],
)

d["financial_evidence"] = section(
    "Financial evidence",
    (
        "From the ingested Stage 1a Screener snapshot (screener_exports/"
        "artha-profile-1-validation.csv, captured 2026-08-30, snapshot_id "
        "above): Market Cap Rs 557.77cr; ROCE 36.81%; ROE 31.76%; D/E 0.18; "
        "OPM 10.43%; 3yr sales growth 131.95%; 3yr profit growth 109.78%; "
        "P/E 7.42x; Artha PEG 0.07; EBIT Rs 103.59cr; Net Working Capital "
        "(ex-cash/debt) Rs 186.59cr; Net Fixed Assets (ex-goodwill) Rs "
        "38.48cr; Enterprise Value Rs 576.43cr; Promoter holding 73.42%, "
        "pledge 0.00%, 3yr trend not present in this export (null, not "
        "assumed flat).\n\n"
        "From secondary web research (FY26, not independently read from "
        "the primary annual report): revenue ~Rs 1,064cr (~3x FY25); PAT "
        "~Rs 75.18cr (vs ~Rs 30.22cr FY25); EBITDA margin ~10.67%; net "
        "margin ~7.06%; order book ~Rs 2,212cr. The Stage 1a OPM (10.43%) "
        "and the secondary-sourced FY26 EBITDA margin (10.67%) are "
        "consistent with each other -- a plausibility cross-check that "
        "corroborates rather than conflicts.\n\n"
        "NOT AVAILABLE: OCF/PAT, gross margin (distinct from OPM), "
        "interest coverage, FCF conversion %, current ratio, "
        "price-to-book, a verified 5yr profit CAGR or EPS-decline history, "
        "and dividend record (none paid to date per secondary sources). "
        "These gaps are carried into Provenance (§14)."
    ),
    [FIN0("Stage 1a fields and secondary-source FY26 figures"), FIN1("reconciliation and data gaps")],
)

d["fatal_flaw_checklist"] = section(
    "Fatal-flaw checklist",
    (
        "Referencing Stage 2 hard-block logic (artha/screening/hard_blocks.py) "
        "against this exact snapshot:\n"
        "- promoter_pledging: PASS (promoter_pledge_pct=0.0, well under the "
        "20% threshold).\n"
        "- promoter_holding_not_declining: the numeric 3yr-trend field is "
        "absent from this export (NEEDS_STAGE_1B on the formal screen), "
        "but the shareholding-governance document's own secondary-source "
        "research describes holding as stable across recent quarters -- "
        "partial corroborating evidence, not a full substitute for the "
        "missing field.\n"
        "- profit_becomes_cash (OCF/PAT>=0.8): NEEDS_STAGE_1B -- not a "
        "field in this export; genuinely unresolved.\n"
        "- survives_worst_year_without_dilution, price_assumption_"
        "plausible: NEEDS_STAGE_3 per the hard-block module's own routing "
        "-- addressed in Pre-Mortem (§9) and Valuation (§7).\n"
        "- no_single_point_of_failure_dependency: addressed directly here. "
        "GGBL's revenue mix spans several segments (solar EPC, module "
        "manufacturing, PM-KUSUM pumps, electrical contracting, water "
        "schemes), which looks diversified on paper. However, a real, "
        "non-diversifiable concentration risk exists: several of these "
        "segments (PM-KUSUM, Jal Jeevan Mission, electrical contracting for "
        "government bodies) are ultimately GOVERNMENT-TENDER-DEPENDENT -- "
        "i.e. GGBL's true customer concentration is 'the Indian government "
        "and state agencies as a channel,' not a single private customer, "
        "but a concentration risk nonetheless, and one this research "
        "cannot rule out.\n"
        "- business_explainable_in_five_sentences: PASS, see §2.\n"
        "- no_serial_equity_dilution: NEEDS_STAGE_1B -- no multi-year "
        "share-count history found.\n"
        "- Greenblatt ranking gate (computed directly against this "
        "snapshot): ROC = EBIT/(NWC+NFA) = 103.59/(186.59+38.48) = 46.03%; "
        "Earnings Yield = EBIT/EV = 103.59/576.43 = 17.97%. ROC rank "
        "100/1101, EY rank 41/1101, combined rank 141, combined percentile "
        "1.73% -- CLEARS the best-decile (<=10%) threshold, one of the "
        "strongest quantitative entry signals in this research batch."
    ),
    [SH0("promoter pledge and shareholding-stability description"), FIN0("EBIT/NWC/NFA/EV inputs for Greenblatt")],
)

d["valuation"] = section(
    "Valuation",
    (
        "Current: Market Cap Rs 557.77cr, EV Rs 576.43cr (EV slightly above "
        "Market Cap, consistent with modest net debt implied by D/E=0.18), "
        "P/E 7.42x -- statistically cheap on its face, and the Greenblatt "
        "combined percentile (1.73%) confirms this is not just a low "
        "trailing P/E but a genuinely strong combined ROC+earnings-yield "
        "rank versus the full 1,101-company universe.\n\n"
        "Stated assumptions (mine, not company guidance):\n"
        "- BEAR CASE: the reported triple-digit 3yr growth decelerates "
        "sharply (it is measured off a small base and cannot repeat "
        "indefinitely); EPC margin compresses under competitive tender "
        "pricing pressure below the current ~10% OPM; the market re-rates "
        "an already-cheap stock even cheaper on growth disappointment. "
        "Rough assumption-driven downside: 30-45% from current levels.\n"
        "- BASE CASE: order-book conversion proceeds roughly as booked "
        "(~Rs 2,212cr over the next 1-2 years), growth decelerates toward "
        "a more moderate (but still healthy, assume 25-40%) pace, margin "
        "holds near current levels. This implies the current cheap "
        "multiple has room to re-rate modestly even without heroic "
        "assumptions -- a genuinely more favorable base case than a "
        "richly-valued name would offer.\n"
        "- BULL CASE: continued order wins, successful capacity expansion "
        "to 2GW by 2027, and diversification into battery storage/EV "
        "charging scale into meaningful new revenue; a rerating toward a "
        "more typical growth-EPC multiple (assume 12-18x vs today's 7.42x) "
        "on a larger earnings base could support substantial (60-100%+) "
        "upside over 2-3 years.\n\n"
        "Overall read: unlike a name priced for perfection, GGBL's 7.42x "
        "P/E and best-decile Greenblatt rank suggest the market is NOT "
        "yet pricing in continued hyper-growth -- but this cheapness may "
        "also reflect the market's own skepticism about growth durability "
        "and EPC-model quality (thin institutional ownership, family-"
        "promoter control, unverified capital-allocation track record), "
        "which is a legitimate alternative explanation for the low "
        "multiple, not just an inefficiency to be arbitraged."
    ),
    [FIN0("Stage 1a valuation multiples"), FIN1("order book vs current revenue scale")],
)

d["buy_below_and_sizing"] = section(
    "Buy-below price and position size",
    (
        "Given the QGLP Price score of 2/3 (§16, genuine cheapness but "
        "tempered by quality/durability uncertainty) and a Jhunjhunwala "
        "conviction score of 3/5 (§23), a buy-below discipline should "
        "still demand SOME discount to the current price given the real "
        "growth-quality and thin-institutional-validation concerns -- "
        "proposed buy-below: roughly 10-15% below current levels, i.e. "
        "closer to a ~6.3-6.7x trailing multiple.\n\n"
        "Position size: config/ips.md caps a fully-sized Track A position "
        "at 2.5% of total investable assets, restricted to 1.25% at the "
        "initial 5% active-sleeve stage (25% single-company sleeve cap). "
        "Given a moderate (not high) conviction score and the genuine "
        "growth-quality caveats in §7/§12, this proposal sizes toward the "
        "lower half of the currently-binding band, subject in every case "
        "to human approval at Gate 1 (plan.md §7.1)."
    ),
    [],
)

d["pre_mortem"] = section(
    "Pre-mortem",
    (
        "It is two years from now (2028) and this position has lost 55%. "
        "What happened: the reported triple-digit 3yr growth turned out to "
        "be exactly the low-base-effect artifact this dossier's own "
        "Disconfirming Evidence (§12) warned about -- growth decelerated "
        "sharply once the order book normalized, and the market, already "
        "skeptical (hence the cheap 7.42x entry multiple), re-rated the "
        "stock even lower rather than higher as the growth story cooled. "
        "Simultaneously, competitive tender pricing in the increasingly "
        "crowded solar-EPC space compressed the already-thin ~10% OPM "
        "toward the mid-single digits, and a working-capital squeeze "
        "(common in EPC models funding large government contracts) forced "
        "either dilutive equity issuance or higher debt -- something this "
        "research could not rule out given the unverified OCF/PAT and "
        "share-count history (§6, §14)."
    ),
    [],
)

d["kill_triggers"] = section(
    "Kill triggers",
    (
        "1. promoter_holding_pct falls below 65% (vs current 73.42%), OR "
        "promoter_pledge_pct rises above 0%.\n"
        "2. OPM falls below 7% for two consecutive reported quarters/years "
        "(vs current ~10.4-10.7%).\n"
        "3. Any disclosed SEBI show-cause order, adverse RPT finding, or "
        "auditor resignation (currently unverified either way).\n"
        "4. No new disclosed order win or order-book update for four "
        "consecutive quarters (a proxy for the order-book-conversion "
        "thesis stalling).\n"
        "5. Sales growth (3yr) falls below 25% in a future snapshot (vs "
        "current 131.95%), signaling the growth thesis has decelerated "
        "well beyond the 'moderation from an unsustainable rate' base "
        "case in §7."
    ),
    [],
)

d["what_would_make_me_add_more"] = section(
    "What would make me add more",
    (
        "A verified (not secondary-sourced) read of the FY2025-26 annual "
        "report confirming: (a) OCF/PAT and a genuine cash-conversion "
        "quality check, (b) the exact related-party-transaction quantum "
        "and a clean, unqualified audit opinion, (c) a disclosed multi-"
        "quarter order-book-to-revenue conversion track record (not just "
        "the booked total), and (d) growing institutional (FII/DII/mutual "
        "fund) participation beyond the current near-zero level, which "
        "would itself be a positive signal that independent analysts have "
        "started validating the numbers this dossier could only source "
        "secondarily."
    ),
    [],
)

d["holding_period_and_tax"] = section(
    "Expected holding period and tax line",
    (
        "Expected holding period: multi-year (Track A compounder thesis, "
        "5+ year window per plan.md §4), contingent on §4's must-be-true "
        "claims continuing to hold at each periodic review. Per "
        "config/ips.md §5, nothing sells before 12 months unless the "
        "thesis has materially broken. Sale within 12 months: STCG (20%); "
        "after 12 months: LTCG (12.5%, Rs 1.25 lakh annual exemption) per "
        "plan.md §2.3 and artha/ledger/tax.py."
    ),
    [],
)

d["disconfirming_evidence"] = section(
    "Disconfirming evidence",
    (
        "The strongest case against this thesis, stated plainly:\n\n"
        "1. The headline 3-year growth figures (131.95% sales, 109.78% "
        "profit) are almost certainly measured off a small revenue base -- "
        "a company scaling to ~Rs 1,064cr FY26 revenue from a much smaller "
        "starting point produces exactly this kind of triple-digit "
        "percentage growth mechanically, and it is structurally easier to "
        "sustain briefly than indefinitely. This dossier found no "
        "independent, multi-year (5+ year) profit history confirming this "
        "is not itself a low-base artifact -- the same concern flagged for "
        "Modi Naturals and Virtual Galaxy in this same research batch.\n\n"
        "2. GGBL's revenue segments (PM-KUSUM, Jal Jeevan Mission, "
        "electrical contracting) are heavily government-tender-dependent -- "
        "a real concentration risk on the demand-channel side, even though "
        "no single private customer dominates (§6).\n\n"
        "3. Zero FII holding and only ~0.76% DII holding (§18) means this "
        "stock currently has essentially no independent institutional "
        "validation of its numbers -- the cheap 7.42x P/E may reflect "
        "genuine market skepticism about growth durability and governance "
        "verifiability, not a market inefficiency waiting to be "
        "arbitraged.\n\n"
        "4. OCF/PAT, related-party-transaction quantum, auditor identity/"
        "opinion, and a multi-year share-count (dilution) history were ALL "
        "genuinely unverified in this research pass (§14) -- an investor "
        "relying only on this dossier is trusting reported accrual profit "
        "and a clean-on-its-face governance story without independent "
        "confirmation of either."
    ),
    [FIN1("small revenue base underlying the reported growth rates"), SH0("zero FII / minimal DII participation"), SH1("unverified RPT/auditor status")],
)

d["provenance"] = {
    "model": "claude-sonnet-5",
    "prompt_version": "manual-harness-v1",
    "documents_read": ["GGBL_BUSINESS_OVERVIEW", "GGBL_FINANCIAL_HIGHLIGHTS", "GGBL_SHAREHOLDING_GOVERNANCE"],
    "could_not_verify": [
        "Exact related-party-transaction quantum/terms",
        "Statutory auditor identity, tenure, and audit-opinion status",
        "Any primary-source concall transcript or annual-report MD&A letter (only financial-portal secondary summaries were available)",
        "A genuine 5-year PAT CAGR / EPS-decline history distinguishing durable growth from a low-base artifact",
        "OCF/PAT, gross margin (distinct from OPM), interest coverage, FCF conversion % -- not present in this Profile 1 Stage 1a export",
        "Multi-year EBIT/invested-capital time series needed to compute ROIIC (only a single-period snapshot was available)",
        "Order-book-to-revenue conversion track record beyond the single booked total figure",
        "Full Pabrai Downside-Floor Score /16 sub-components requiring balance-sheet detail beyond Stage 1a fields",
    ],
}

d["moat_understandability_gate"] = {
    "passed": True,
    "moat_type": "niche_specialization_policy_tailwind",
    "moat_evidence": (
        "GGBL's stated differentiator is government-tender expertise and "
        "decentralized rural solar execution (PM-KUSUM pumps, rural "
        "electrification) -- a specialization niche within the broader, "
        "more fragmented and competitive solar-EPC industry, reinforced by "
        "a structural policy tailwind (India's domestic-manufacturing push "
        "and renewable-capacity targets). This is a moderate, "
        "policy-dependent moat, weaker than a brand/network-effect/"
        "switching-cost moat -- EPC execution is not inherently hard to "
        "replicate, and the moat rests substantially on GGBL's existing "
        "government relationships and tender track record rather than a "
        "structural cost or technology advantage."
    ),
    "return_trend_summary": (
        "Only a single-period Stage 1a snapshot was available (ROCE=36.81%, "
        "ROE=31.76%) -- a multi-year ROE/ROIC-vs-WACC trend could not be "
        "established. The secondary-sourced FY26-vs-FY25 PAT comparison "
        "(~Rs 75.18cr vs ~Rs 30.22cr) is a single year-over-year data "
        "point, not a verified multi-year series."
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
        "This fails if: (a) the order book fails to convert at the "
        "reported margin, exposing the triple-digit growth as a base-"
        "effect artifact; (b) government-tender flow slows (policy shift "
        "or budget constraints); (c) EPC-sector tender-price competition "
        "compresses margin below sustainable levels; or (d) an "
        "unverified RPT/auditor/dilution issue (§14) turns out to hide a "
        "real governance problem once independently confirmed. NOTE: this "
        "gate is passed with real caveats on management_understandability "
        "and industry_structure_stability specifically -- the evidence is "
        "thinner (named promoters + stated capacity/order-book plans, but "
        "no primary-source concall/MD&A letter) than for Kothari "
        "Petrochemicals in this same research batch, and a stricter reader "
        "could reasonably fail this gate on that basis; recorded honestly "
        "as a judgment call, not a certainty."
    ),
    "citations": [BIZ0("niche positioning and asset-light EPC model"), FIN0("FY26 order book and growth figures"), SH0("promoter family identity")],
}

d["qglp_scorecard"] = {
    "quality": 2,
    "growth": 1,
    "longevity": 1,
    "price": 2,
    "evidence": {
        "Q": (
            "ROE 31.76% and ROCE 36.81% both clear the >=15% (ideal >=20%) "
            "threshold with real margin; D/E 0.18 is comfortably under 1.0. "
            "Held to 2 (not 3) because OCF/PAT (cash-conversion quality) is "
            "not available in this export and the 3yr promoter-holding "
            "trend field is also absent -- both genuine, named gaps."
        ),
        "G": (
            "3yr sales growth 131.95% and profit growth 109.78% are far "
            "above the >=20% ideal band on their face, but this dossier's "
            "own Disconfirming Evidence (§12) flags this as very likely a "
            "small-base artifact, with no independently verified 5-year "
            "CAGR or EPS-decline history. Scored conservatively at 1 given "
            "the unverified multi-year consistency and the single-source, "
            "single-year-over-year secondary FY26 comparison."
        ),
        "L": (
            "A plausible but genuinely thin moat case: a policy-tailwind-"
            "dependent niche (government tenders, PM-KUSUM) rather than a "
            "structural cost/technology/brand advantage, plus an unverified "
            "multi-year management capital-allocation track record beyond "
            "stated expansion plans. Scored 1 -- durability is plausible "
            "but speculative, not a slam-dunk case."
        ),
        "P": (
            "P/E 7.42x, PEG 0.07, and a best-decile Greenblatt combined "
            "percentile (1.73%) are all genuinely cheap signals -- but the "
            "near-zero institutional (FII/DII) participation raises the "
            "alternative explanation that the market is pricing in real "
            "skepticism about growth durability and governance "
            "verifiability, not offering a free lunch. Scored 2 -- fair "
            "to cheap, real margin-of-safety evidence, but not awarded a 3 "
            "given the unresolved quality questions in Q and G above."
        ),
    },
    "citations": [FIN0("Stage 1a financial figures"), SH0("institutional participation levels")],
}

d["margin_of_safety_scuttlebutt"] = section(
    "Margin-of-Safety & Scuttlebutt Notes",
    (
        "GRAHAM DEFENSIVE-INVESTOR CRITERIA (relaxed for India):\n"
        "- Current ratio >=2.0: UNKNOWN -- not present in this export.\n"
        "- No earnings deficit in 10 years: UNKNOWN -- no history "
        "available; GGBL's own listing/scale history is itself recent per "
        "the FY26 '3x revenue jump' description, so a genuine 10-year "
        "record may not even exist yet in a meaningful form.\n"
        "- P/E <=15x on 3yr average EPS: PASS on trailing P/E (7.42x, well "
        "under 15x) though a true 3yr-average-EPS figure was not computed.\n"
        "- P/B <=1.5x: UNKNOWN -- price_to_book not present.\n"
        "- Graham Number (P/E x P/B <=22.5): UNKNOWN -- needs P/B.\n"
        "- Dividend record >=10 years: FAIL/NOT APPLICABLE -- no dividend "
        "paid to date per secondary sources.\n"
        "- Margin of safety vs intrinsic value: not computed with false "
        "precision -- see Valuation (§7)'s explicit scenario assumptions.\n\n"
        "FISHER'S 15-POINT SCUTTLEBUTT CHECKLIST (digital proxies):\n"
        "1. Sufficient market potential: PASS -- India's solar-policy "
        "tailwind (BIZ1).\n"
        "2. Management determined on new products/processes: PARTIAL -- "
        "stated battery-storage/EV-charging diversification plans (BIZ2), "
        "not independently verified beyond a secondary summary.\n"
        "3. R&D effectiveness: UNKNOWN -- no evidence found.\n"
        "4. Above-average sales organization: PARTIAL -- a Rs 2,212cr "
        "order book (FIN0) is some evidence of sales execution capability.\n"
        "5. Worthwhile profit margin: PARTIAL -- OPM ~10.4-10.7% (FIN0) is "
        "modest, typical of EPC/contracting, not a high-margin business.\n"
        "6. Doing what to improve margin: UNKNOWN -- no management "
        "commentary on margin strategy found.\n"
        "7-8. Labor/executive relations: UNKNOWN.\n"
        "9. Depth of management: PARTIAL -- named promoter family (Patels, "
        "SH0) but no evidence of professional management bench depth "
        "beyond the family.\n"
        "10. Cost analysis/accounting controls: UNKNOWN -- not "
        "independently verified.\n"
        "11. Industry-specific differentiators: PASS -- decentralized "
        "rural execution and government-tender niche (BIZ0).\n"
        "12. Profit outlook: PARTIAL -- order book gives some forward "
        "visibility (FIN0), but no management guidance quote found.\n"
        "13. Equity financing needs: UNKNOWN -- D/E=0.18 suggests no "
        "current heavy reliance on debt, but no disclosed financing plan.\n"
        "14. Candour with investors: UNKNOWN -- no concall/annual-report "
        "commentary was found in this research pass (a real gap versus "
        "the Ecoreco precedent dossier, which had at least one secondary "
        "concall summary).\n"
        "15. Management integrity: addressed separately as the Integrity "
        "Gate (§18)."
    ),
    [BIZ0("industry positioning"), BIZ2("diversification plans"), FIN0("order book and margin"), SH0("promoter identity")],
)

d["integrity_gate"] = {
    "passed": True,
    "promoter_pledge_flag": False,
    "declining_holding_flag": False,
    "rpt_or_auditor_or_sebi_flag": False,
    "evidence": (
        "promoter_pledge_pct=0.0 confirmed directly from the Stage 1a "
        "snapshot. The 3yr promoter-holding-trend field is absent from "
        "this export, but the shareholding-governance document's own "
        "secondary research describes holding as stable across recent "
        "quarters (SH0) -- treated as sufficient (not conclusive) evidence "
        "of non-declining holding, rather than assumed favorable with no "
        "evidence at all. No SEBI show-cause order, adverse RPT finding, "
        "or auditor resignation was found referenced in the sources "
        "consulted (multiple queries). HOWEVER, this is an absence of "
        "finding in general public research, not an exhaustive review of "
        "SEBI's enforcement database or GGBL's full exchange-filing "
        "history -- the exact RPT quantum and auditor identity/opinion "
        "were NOT independently confirmed, and this gap is carried into "
        "Provenance (§14) rather than treated as fully verified."
    ),
    "citations": [SH0("promoter pledge and holding stability"), SH1("absence of adverse-finding search results")],
}

d["scale_economies_shared"] = section(
    "Scale Economies Shared Assessment",
    (
        "ROIIC: could NOT be computed -- only a single-period Stage 1a "
        "snapshot was available; reporting an estimated ROIIC from one "
        "period would be a fabricated number with false precision.\n\n"
        "A RELATED, single-period Greenblatt-style ROC (NOT ROIIC): EBIT / "
        "(NWC ex-cash-ex-debt + NFA ex-goodwill) = 103.59 / (186.59+38.48) "
        "= 46.03% -- a very strong return-on-capital-employed proxy, "
        "consistent with an asset-light EPC model that requires relatively "
        "little fixed-asset investment per rupee of contract value.\n\n"
        "VOLUME VS. PRICE: no management quote distinguishing volume "
        "growth (more projects/MW executed) from price/margin increases "
        "was found. The order-book/capacity-expansion narrative (FIN0) is "
        "more consistent with a volume-driven growth story than a "
        "price-increase-driven one, but this is an inference, not a "
        "direct quote.\n\n"
        "VERDICT: insufficient direct evidence for a confident moat-"
        "widening call on Sleep's specific volume-vs-price test. The "
        "strong single-period ROC is a positive but distinct signal, not a "
        "substitute for genuine ROIIC evidence."
    ),
    [FIN0("EBIT/NWC/NFA inputs"), FIN0("order book as volume-growth proxy evidence")],
)

d["magic_formula_attribution"] = section(
    "Magic Formula Attribution",
    (
        "Quantitative-entry note reporting the Stage 2 Greenblatt ranking "
        "gate's result, not a standalone buy case.\n\n"
        "ROC = EBIT / (NWC ex-cash-ex-debt + NFA ex-goodwill) = 103.59 / "
        "225.07 = 46.03%.\n"
        "Earnings Yield = EBIT / EV = 103.59 / 576.43 = 17.97%.\n\n"
        "Ranked against the full 1,101-company rankable universe from this "
        "snapshot: ROC rank 100th, Earnings Yield rank 41st, combined rank "
        "141, combined percentile 1.73% -- CLEARS the best-decile (<=10%) "
        "threshold, one of the strongest combined ROC+EY signals of the "
        "20-stock shortlist this dossier was drawn from.\n\n"
        "Profile 1 (profile_1_standard) uses Greenblatt's own EBIT-based "
        "ROC/EV method directly -- no sector-native substitution required."
    ),
    [FIN0("EBIT, NWC, NFA, EV inputs")],
)

d["conviction_sizing"] = section(
    "Super-Investor Alignment / Cloning & Conviction Sizing",
    (
        "PABRAI DOWNSIDE-FLOOR SCORE (/16): could not be scored in full. "
        "Debt safety looks reasonable (D/E=0.18) but net-cash/tangible-"
        "asset backing, bear-case FCF survival, and liquidation-value "
        "coverage all require balance-sheet detail not available here. "
        "Reporting a fabricated /16 total would misrepresent confidence "
        "that isn't there.\n"
        "ASYMMETRY RATIO: using this dossier's own Valuation assumptions "
        "(§7) -- an assumed ~30-45% bear-case downside against an assumed "
        "~60-100% bull-case upside -- gives a rough asymmetry ratio in the "
        "neighborhood of 1.5:1 to 3:1, at the edge of but not decisively "
        "clearing Pabrai's >=3:1 threshold. Built from this dossier's own "
        "scenario assumptions, not an independently verified calculation.\n\n"
        "No cross-reference to a known Indian super-investor's disclosed "
        "shareholding was found for this candidate.\n\n"
        "JHUNJHUNWALA CONVICTION SCORE: 3/5. Business clarity is "
        "reasonable (clean, understandable EPC/manufacturing story, §2/"
        "§15); management-quality checks are thin (no concall/primary-"
        "source evidence found, §14); FCF/PAT reconciliation could not be "
        "done; thesis specificity is reasonable (a specific order book and "
        "capacity-expansion plan, §3); disconfirming-evidence adequacy is "
        "genuine (§12 raises real, unresolved concerns). Not a return "
        "forecast -- it only modulates sizing, subject to human override "
        "at Gate 1.\n\n"
        "PROPOSED POSITION SIZE (proposal only): given the moderate (3/5) "
        "conviction score, size toward the lower half of the currently-"
        "binding Track A band per config/ips.md (up to 1.25% of total "
        "investable assets at the current 5% active-sleeve stage), "
        "subject to Gate 1/Gate 2 human approval."
    ),
    [FIN0("D/E input for debt-safety read")],
)

d["quality_compounding_checklist"] = section(
    "Quality-Compounding Checklist",
    (
        "ROCE: 36.81% (single latest-period figure; a multi-year trend "
        "could not be established).\n"
        "Gross margin (distinct from OPM), interest coverage, and FCF "
        "conversion %: NOT AVAILABLE -- none present in this export or "
        "found in secondary research.\n\n"
        "REINVESTMENT-RUNWAY RATIONALE: the stated capacity expansion "
        "(1.1 GW to 2 GW by 2027, FIN0) plus a Rs 2,212cr order book "
        "against ~Rs 1,064cr FY26 revenue suggests a credible, cited "
        "reinvestment runway if the order book converts as booked and "
        "India's solar-policy tailwind continues -- a specific, evidenced "
        "case rather than generic optimism.\n\n"
        "SMITH'S 'DO NOTHING' DISCIPLINE: 'do nothing' means not selling "
        "absent genuine thesis impairment. Specific evidence that WOULD "
        "impair this thesis (feeding Kill Triggers, §10): OPM falling "
        "below 7% for two consecutive periods, order-book conversion "
        "stalling, loss of government-tender momentum, or confirmation of "
        "an adverse RPT/auditor finding once the currently-unverified "
        "items in §14 are resolved."
    ),
    [FIN0("ROCE and order book/capacity figures")],
)

with open("run-ggbl-20260830-001.json", "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print("wrote run-ggbl-20260830-001.json,", len(json.dumps(d)), "bytes")
