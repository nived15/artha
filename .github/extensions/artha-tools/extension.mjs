// Extension: artha-tools
//
// Phase 3a (implementation_plan.md §4): the read-only tool surface for
// Artha's dossier-generation agents, plus the artha-dossier Agent Factory
// that orchestrates them. No write/order tools live here — the factory's
// own write step (below) is server-side orchestration code, not an
// agent-callable tool, matching the plan's "no research agent should ever
// be one tool-call away from placing an order" safety property.
//
// Every tool is a thin JSON-in/JSON-out wrapper over the Python CLI's
// `artha agent-tools ...` commands (artha/cli/main.py) — the deterministic
// Python core owns the data; this extension only shells out to it.

import { defineFactory, joinSession } from "@github/copilot-sdk/extension";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const REPO_ROOT = process.cwd();

function resolvePython() {
    const candidates = [
        path.join(REPO_ROOT, ".venv", "Scripts", "python.exe"), // Windows venv
        path.join(REPO_ROOT, ".venv", "bin", "python"), // POSIX venv
    ];
    for (const candidate of candidates) {
        if (existsSync(candidate)) return candidate;
    }
    return "python"; // fall back to whatever is on PATH
}

const PYTHON = resolvePython();

/**
 * Run `python -m artha.cli.main agent-tools <args...>`, optionally piping
 * `stdin` in, and return { exitCode, stdout, stderr }. Never throws for a
 * non-zero exit — the CLI's own convention is to print a JSON {"error":
 * ...} body on expected failures (not found, invalid draft, etc.), which
 * callers should surface to the agent as useful information, not a hard
 * tool failure.
 */
function runArthaCli(args, { stdin } = {}) {
    return new Promise((resolve, reject) => {
        const child = spawn(PYTHON, ["-m", "artha.cli.main", "agent-tools", ...args], {
            cwd: REPO_ROOT,
            stdio: ["pipe", "pipe", "pipe"],
        });

        let stdout = "";
        let stderr = "";
        child.stdout.on("data", (chunk) => (stdout += chunk));
        child.stderr.on("data", (chunk) => (stderr += chunk));
        child.on("error", reject);
        child.on("close", (exitCode) => resolve({ exitCode, stdout: stdout.trim(), stderr: stderr.trim() }));

        if (stdin !== undefined) {
            child.stdin.write(stdin);
        }
        child.stdin.end();
    });
}

/** Shared handler shape: run the CLI, and turn its JSON stdout into the
 * tool result. A non-JSON stdout (a genuine crash, not an expected
 * "not found"/"invalid" case) is reported as a tool failure. */
async function jsonTool(args, { stdin } = {}) {
    const { exitCode, stdout, stderr } = await runArthaCli(args, { stdin });
    if (!stdout) {
        return { textResultForLlm: stderr || `artha-tools CLI exited ${exitCode} with no output`, resultType: "failure" };
    }
    try {
        JSON.parse(stdout); // validate it really is JSON before handing it back
        return { textResultForLlm: stdout, resultType: "success" };
    } catch {
        return { textResultForLlm: `non-JSON output (exit ${exitCode}): ${stdout}\n${stderr}`, resultType: "failure" };
    }
}

// --- JSON schemas mirroring artha/dossier/schema.py exactly (see the
// artha-dossier-json-schema skill) — used as ctx.agent's `schema` option so
// each subagent's final text is parsed into a JS object directly, instead
// of the factory having to re-parse free text itself. --------------------

const CITATION_SCHEMA = {
    type: "object",
    required: ["doc_id", "page"],
    properties: {
        doc_id: { type: "string" },
        page: { type: "integer" },
        note: { type: "string" },
    },
};

const DOSSIER_SECTION_SCHEMA = {
    type: "object",
    required: ["title", "content", "citations"],
    properties: {
        title: { type: "string" },
        content: { type: "string" },
        citations: { type: "array", items: CITATION_SCHEMA },
    },
};

const MOAT_GATE_SCHEMA = {
    type: "object",
    required: [
        "passed",
        "moat_type",
        "moat_evidence",
        "return_trend_summary",
        "five_sentence_test_result",
        "understandability_checklist",
        "inversion_summary",
        "citations",
    ],
    properties: {
        passed: { type: "boolean" },
        moat_type: { type: "string" },
        moat_evidence: { type: "string" },
        return_trend_summary: { type: "string" },
        five_sentence_test_result: { type: "string" },
        understandability_checklist: {
            type: "object",
            required: [
                "five_sentence_business_model",
                "unit_economics_clarity",
                "industry_structure_stability",
                "demand_forecastability_5_10yr",
                "management_understandability",
                "accounting_transparency",
                "identifiable_moat_source",
            ],
            properties: {
                five_sentence_business_model: { type: "boolean" },
                unit_economics_clarity: { type: "boolean" },
                industry_structure_stability: { type: "boolean" },
                demand_forecastability_5_10yr: { type: "boolean" },
                management_understandability: { type: "boolean" },
                accounting_transparency: { type: "boolean" },
                identifiable_moat_source: { type: "boolean" },
            },
        },
        inversion_summary: { type: "string" },
        citations: { type: "array", items: CITATION_SCHEMA },
    },
};

const QGLP_SCHEMA = {
    type: "object",
    required: ["quality", "growth", "longevity", "price", "evidence", "citations"],
    properties: {
        quality: { type: "integer" },
        growth: { type: "integer" },
        longevity: { type: "integer" },
        price: { type: "integer" },
        evidence: {
            type: "object",
            required: ["Q", "G", "L", "P"],
            properties: { Q: { type: "string" }, G: { type: "string" }, L: { type: "string" }, P: { type: "string" } },
        },
        citations: { type: "array", items: CITATION_SCHEMA },
    },
};

const INTEGRITY_GATE_SCHEMA = {
    type: "object",
    required: [
        "passed",
        "promoter_pledge_flag",
        "declining_holding_flag",
        "rpt_or_auditor_or_sebi_flag",
        "evidence",
        "citations",
    ],
    properties: {
        passed: { type: "boolean" },
        promoter_pledge_flag: { type: "boolean" },
        declining_holding_flag: { type: "boolean" },
        rpt_or_auditor_or_sebi_flag: { type: "boolean" },
        evidence: { type: "string" },
        citations: { type: "array", items: CITATION_SCHEMA },
    },
};

// Every framework/extraction section (§15-24) uses one of the two gate
// shapes, the QGLP shape, or the generic DossierSection shape.
const FRAMEWORK_SECTION_SCHEMAS = {
    moat_understandability_gate: MOAT_GATE_SCHEMA,
    qglp_scorecard: QGLP_SCHEMA,
    margin_of_safety_scuttlebutt: DOSSIER_SECTION_SCHEMA,
    integrity_gate: INTEGRITY_GATE_SCHEMA,
    scale_economies_shared: DOSSIER_SECTION_SCHEMA,
    magic_formula_attribution: DOSSIER_SECTION_SCHEMA,
    conviction_sizing: DOSSIER_SECTION_SCHEMA,
    davis_double_play: DOSSIER_SECTION_SCHEMA,
    quality_compounding_checklist: DOSSIER_SECTION_SCHEMA,
    canslim_notes: DOSSIER_SECTION_SCHEMA,
};

const CITATION_VERIFICATION_SCHEMA = {
    type: "object",
    required: ["all_citations_verified", "unsupported_claims"],
    properties: {
        all_citations_verified: { type: "boolean" },
        unsupported_claims: {
            type: "array",
            items: {
                type: "object",
                properties: {
                    claim: { type: "string" },
                    citation: CITATION_SCHEMA,
                    reason: { type: "string" },
                },
            },
        },
        notes: { type: "string" },
    },
};

// Sections 1-14 — identity + narrative sections + provenance — owned by
// the artha-dossier-narrative agent (.github/agents/artha-dossier-narrative.md).
// Only these keys are required here; the framework sections (§15-24) are
// merged in deterministically by the factory itself from the already-
// verified subagent outputs, not trusted from this agent's transcription
// (implementation_plan.md §4/§6: assembly operates on already-condensed
// section outputs, and identity must never be guessed).
const NARRATIVE_SCHEMA = {
    type: "object",
    required: [
        "identity",
        "business_five_sentences",
        "why_now",
        "three_things_must_be_true",
        "financial_evidence",
        "fatal_flaw_checklist",
        "valuation",
        "buy_below_and_sizing",
        "pre_mortem",
        "kill_triggers",
        "what_would_make_me_add_more",
        "disconfirming_evidence",
        "holding_period_and_tax",
        "provenance",
    ],
    properties: {
        identity: {
            type: "object",
            required: ["company", "ticker", "sector", "arithmetic_profile", "track", "date", "pipeline_run_id", "snapshot_id"],
            properties: {
                company: { type: "string" },
                ticker: { type: "string" },
                sector: { type: "string" },
                arithmetic_profile: { type: "string" },
                track: { type: "string", enum: ["A", "B"] },
                date: { type: "string" },
                pipeline_run_id: { type: "string" },
                snapshot_id: { type: "string" },
            },
        },
        business_five_sentences: DOSSIER_SECTION_SCHEMA,
        why_now: DOSSIER_SECTION_SCHEMA,
        three_things_must_be_true: DOSSIER_SECTION_SCHEMA,
        financial_evidence: DOSSIER_SECTION_SCHEMA,
        fatal_flaw_checklist: DOSSIER_SECTION_SCHEMA,
        valuation: DOSSIER_SECTION_SCHEMA,
        buy_below_and_sizing: DOSSIER_SECTION_SCHEMA,
        pre_mortem: DOSSIER_SECTION_SCHEMA,
        kill_triggers: DOSSIER_SECTION_SCHEMA,
        what_would_make_me_add_more: DOSSIER_SECTION_SCHEMA,
        disconfirming_evidence: DOSSIER_SECTION_SCHEMA,
        holding_period_and_tax: DOSSIER_SECTION_SCHEMA,
        provenance: {
            type: "object",
            required: ["model", "prompt_version", "documents_read", "could_not_verify"],
            properties: {
                model: { type: "string" },
                prompt_version: { type: "string" },
                documents_read: { type: "array", items: { type: "string" } },
                could_not_verify: { type: "array", items: { type: "string" } },
            },
        },
    },
};

const session = await joinSession({
    tools: [
        {
            name: "get_filing_chunk",
            description:
                "Read one exact citation chunk (doc_id, page[, chunk_index]) from the filing chunk store. " +
                "Every factual claim in a dossier must cite a (doc_id, page) from this store — plan.md §6.",
            parameters: {
                type: "object",
                properties: {
                    doc_id: { type: "string", description: "The filing's doc_id, from get_candidate or list_candidate_chunks." },
                    page: { type: "integer", description: "1-indexed page number within the filing." },
                    chunk_index: { type: "integer", description: "Chunk index within the page (default 0)." },
                },
                required: ["doc_id", "page"],
            },
            handler: async (args) => {
                const cliArgs = ["get-filing-chunk", String(args.doc_id), String(args.page)];
                if (args.chunk_index !== undefined) cliArgs.push("--chunk-index", String(args.chunk_index));
                return jsonTool(cliArgs);
            },
        },
        {
            name: "get_candidate",
            description:
                "Look up one candidate's resolved Stage 1a screening fields (ROE, ROCE, promoter holding, etc.) " +
                "for a given ticker within a specific data snapshot — the candidate + snapshot ID a screening run produced.",
            parameters: {
                type: "object",
                properties: {
                    ticker: { type: "string" },
                    snapshot_id: { type: "string", description: "The content-addressable snapshot ID (artha.data.snapshot) to look the candidate up within." },
                },
                required: ["ticker", "snapshot_id"],
            },
            handler: async (args) => jsonTool(["get-candidate", String(args.ticker), "--snapshot-id", String(args.snapshot_id)]),
        },
        {
            name: "list_candidate_chunks",
            description:
                "List citation chunks from every filing ingested for a ticker, optionally filtered to chunks " +
                "containing a topic keyword (case-insensitive substring match). Use this to find which (doc_id, page) " +
                "to cite for a given claim before calling get_filing_chunk.",
            parameters: {
                type: "object",
                properties: {
                    ticker: { type: "string" },
                    topic: { type: "string", description: "Optional keyword to filter chunks by (e.g. 'pledge', 'related party')." },
                },
                required: ["ticker"],
            },
            handler: async (args) => {
                const cliArgs = ["list-candidate-chunks", String(args.ticker)];
                if (args.topic) cliArgs.push("--topic", String(args.topic));
                return jsonTool(cliArgs);
            },
        },
        {
            name: "validate_dossier",
            description:
                "Validate a draft dossier (the full 24-section JSON structure) against plan.md §6's completeness and " +
                "citation-presence rules, WITHOUT writing it anywhere. Returns {passed, errors: [{section, reason}]}. " +
                "Always call this before assembly is considered done — it is the deterministic backstop, not a formality.",
            parameters: {
                type: "object",
                properties: {
                    draft: { type: "object", description: "The full dossier draft, matching artha.dossier.schema.Dossier's field names." },
                },
                required: ["draft"],
            },
            handler: async (args) => jsonTool(["validate-dossier"], { stdin: JSON.stringify(args.draft) }),
        },
    ],
    factories: [
        defineFactory({
            meta: {
                name: "artha-dossier",
                description:
                    "Generate one candidate's 24-section dossier (plan.md §6) end to end: fan out one subagent per " +
                    "framework/extraction dimension, run an adversarial citation-verification pass, assemble and " +
                    "validate the result, then write it. args: { ticker: string, snapshot_id: string, track: 'A' | 'B' }.",
                phases: [
                    { title: "Fan-out", detail: "One subagent per framework/extraction section" },
                    { title: "Citation verification", detail: "Adversarial re-check of every cited claim" },
                    { title: "Assemble & validate", detail: "Deterministic completeness/citation gate (artha.dossier.validator)" },
                    { title: "Write", detail: "dossiers/<ticker>/<run_id>.md + SQLite index + journal" },
                ],
                argsSchema: {
                    type: "object",
                    required: ["ticker", "snapshot_id", "track"],
                    properties: {
                        ticker: { type: "string" },
                        snapshot_id: { type: "string" },
                        track: { type: "string", enum: ["A", "B"] },
                    },
                },
                limits: {
                    // Matches artha/config/schema.py's BudgetConfig defaults
                    // (implementation_plan.md §16 Q5) — soft, post-paid ceilings.
                    maxConcurrentSubagents: 5,
                    maxTotalSubagents: 20,
                    maxAiCredits: 5,
                    timeoutSeconds: 3600,
                },
            },
            run: async (ctx) => {
                ctx.phase("Fan-out");

                const candidateResult = await ctx.step("fetch-candidate-v1", async () => {
                    const { exitCode, stdout } = await runArthaCli([
                        "get-candidate",
                        ctx.args.ticker,
                        "--snapshot-id",
                        ctx.args.snapshot_id,
                    ]);
                    try {
                        return { exitCode, data: JSON.parse(stdout) };
                    } catch {
                        return { exitCode, data: { error: stdout || "no output" } };
                    }
                });

                if (candidateResult.exitCode !== 0 || candidateResult.data.error) {
                    ctx.log(`candidate lookup failed: ${JSON.stringify(candidateResult.data)}`);
                    return { error: "candidate_not_found", detail: candidateResult.data };
                }

                const candidate = candidateResult.data;
                const track = ctx.args.track;

                // One subagent per framework/extraction dimension (plan.md §6
                // sections 15-24). NOTE: FactoryAgentOptions.agent ("Optional
                // custom agent name for the subagent") is currently accepted
                // but NOT YET HONORED by this SDK build (confirmed against
                // generated/rpc.d.ts) — every subagent actually runs as a
                // generic agent with no .github/agents/*.md system prompt
                // applied. So each job's full task-specific instructions
                // (condensed from its .md file) must be embedded directly in
                // the prompt text below, not merely implied by which named
                // agent is requested. `agent: job.agent` is still passed for
                // forward compatibility once the SDK does honor it, but the
                // prompt text alone must be self-sufficient today. This
                // matters especially because several jobs below share the
                // identical generic DOSSIER_SECTION_SCHEMA shape ({title,
                // content, citations}) — without distinct prompt text, the
                // model has no way to tell which section it is writing.
                const FRAMEWORK_INSTRUCTIONS = {
                    moat_understandability_gate:
                        "Assess dossier §15 — the Moat & Understandability Gate (Buffett & Munger). This is a GATE. " +
                        "Identify the moat type (brand / switching_cost / network_effect / cost_advantage / efficient_scale_regulatory / none) with cited evidence. " +
                        "Summarize the 10-year ROE/ROIC-vs-WACC trend (or say exactly what you could verify). Apply the five-sentence business-model test. " +
                        "Score the 7-gate understandability checklist (five_sentence_business_model, unit_economics_clarity, industry_structure_stability, " +
                        "demand_forecastability_5_10yr, management_understandability, accounting_transparency, identifiable_moat_source), each true/false with a one-line reason. " +
                        "Write an inversion summary (what would make this fail). Decide passed=true only if every one of the 7 gates passed — no partial credit.",
                    qglp_scorecard:
                        "Score dossier §16 — the QGLP Scorecard (Raamdeo Agrawal): Quality/Growth/Longevity/Price, each 0-3, scored in that order with Price scored last by design. " +
                        "Quality: ROE/ROCE >=15% (>=20% ideal), D/E <=1.0, OCF/PAT >=0.8, promoter holding >=50% and not declining. " +
                        "Growth: PAT CAGR >=15%/5yr (>=20% ideal), no year of EPS decline if verifiable. " +
                        "Longevity: qualitative judgment — durable reasons to keep compounding for years, grounded in cited evidence. " +
                        "Price (scored last): is the current price fair-to-cheap given the Q/G/L just found, or already pricing in flawless execution? " +
                        "Write one cited evidence sentence per letter (Q/G/L/P).",
                    margin_of_safety_scuttlebutt:
                        "Write dossier §17 — Margin-of-Safety & Scuttlebutt Notes, combining two frameworks. " +
                        "Part 1 (Graham, relaxed for India): current ratio >=2.0; no earnings deficit in 10yr (say so if unverifiable, don't assume a pass); " +
                        "P/E <=15x on 3yr avg EPS; P/B <=1.5x; Graham Number ceiling P/E*P/B<=22.5; dividend record relaxed to >=10 consecutive years. " +
                        "Report pass/fail/unknown per criterion with evidence, and your own margin-of-safety estimate vs. an intrinsic-value estimate (state method/assumptions). " +
                        "Part 2 (Fisher's 15-point scuttlebutt checklist via digital proxies): concall candour/evasion, analyst/competitor commentary, governance signals, " +
                        "R&D/patent signals, channel/distributor mentions — score each pass/partial/fail/unknown with cited evidence. 'Unknown' is an honest answer, not a failure.",
                    integrity_gate:
                        "Assess dossier §18 — the Super-Investor Integrity Gate (Fisher Point 15 + Agrawal governance signals). This is a GATE. " +
                        "Check promoter_pledge_pct (fails closed — missing/unresolvable pledge data is itself a gate failure, not a pass-by-default) and " +
                        "promoter_holding_trend_3y (a declining trend is itself a red flag). Search filings (topics like SEBI, related party, auditor, resignation) for any " +
                        "SEBI show-cause order, adverse related-party transaction, or auditor resignation within the last 5 years — any one of these is a single bad-faith signal " +
                        "that no other strength offsets. Decide passed=false if pledge >20%, holding is declining, or any RPT/auditor/SEBI flag fired; otherwise true. " +
                        "If you cannot verify the pledge figure at all, set promoter_pledge_flag=true and passed=false.",
                    scale_economies_shared:
                        "Write dossier §20 — the Scale Economies Shared Assessment (Nick Sleep & early Buffett), relevant where pricing power (or its deliberate absence) is the thesis. " +
                        "Find explicit management language, quoted and cited, about passing scale-driven cost savings to customers versus extracting margin. " +
                        "Compute ROIIC (Return on Incremental Invested Capital = ΔNOPAT ÷ ΔInvested Capital), one-period lag, 3yr and 5yr windows if establishable from cited filings — " +
                        "show your calculation inputs; ROIIC >=25-30% is the 'genuine compounder' threshold. Decompose growth into volume vs. price wherever the filings let you. " +
                        "Give a verdict: moat-widening / stable / narrowing, with reasoning. If you cannot establish ROIIC inputs, say so explicitly rather than estimating.",
                    magic_formula_attribution:
                        "Write dossier §21 — Magic Formula Attribution (Joel Greenblatt). This is a quantitative-entry note, not a standalone buy case — " +
                        "the deterministic Greenblatt ranking gate already ran at Stage 2 screening; your job is to report and contextualize it, not recompute it. " +
                        "Report ROC and Earnings Yield components/values (ebit, net_working_capital_ex_cash_ex_debt, net_fixed_assets_ex_goodwill, enterprise_value from get_candidate). " +
                        "State ordinal rank/percentile within the Stage-2 universe only if that context is available to you; otherwise report the raw figures and note ranking happens at screening. " +
                        "If this is a Profile 2-5 candidate, explicitly disclose that the rank uses Artha's own sector-native substitution, never Greenblatt's original method — required attribution honesty. " +
                        "Do not use this section to make a buy case on its own.",
                    conviction_sizing:
                        "Write dossier §23 — Super-Investor Alignment / Cloning & Conviction Sizing (Pabrai's Dhandho framework + Jhunjhunwala's conviction scoring). " +
                        "Report the Pabrai Downside-Floor Score (/16) and Asymmetry Ratio only if available in your context — say so rather than inventing numbers if not. " +
                        "Note any cited super-investor shareholding cross-reference only with a specific citation, never speculation about 'smart money'. " +
                        "Assemble a 1-5 conviction score from evidence quality (business clarity, management-quality checks, FCF/PAT reconciliation, thesis specificity, " +
                        "disconfirming-evidence adequacy) — explicitly state this is never a return forecast and is always subject to human override at Gate 1. " +
                        "Map the conviction score to a proposed position size within the track's sizing band (Track A: 2-3% of investable assets; Track B: 1-1.5%), framed as a proposal, not a decision.",
                    davis_double_play:
                        "Write dossier §19 — The Davis Double Play Mechanism (Shelby Davis) — Track B only. " +
                        "Report entry P/E, and whether trailing EPS growth is >=15% together with reported acceleration (latest-quarter EPS YoY and TTM-vs-prior-TTM both positive and improving). " +
                        "Forward/consensus EPS estimates are deliberately excluded — never use one even if you find one mentioned in a filing. " +
                        "State a sector-median P/E re-rating target only if establishable from cited peer comparisons — otherwise say so rather than inventing a peer set. " +
                        "Compute the implied multiplicative return using: (1 + trailing EPS CAGR)^3 × (sector-median P/E ÷ entry P/E) − 1 — never additive — showing your inputs and the resulting implied return/CAGR. " +
                        "Flag the 'double play in reverse' risk: could earnings AND the multiple fall together? Name the specific scenario, grounded in the filings.",
                    quality_compounding_checklist:
                        "Write dossier §22 — the Quality-Compounding Checklist (Terry Smith) — Track A only. " +
                        "Report the ROCE trend, FCF conversion % (FCF/Net Income), gross margin versus sector (cite a comparison or state you could not establish one), and interest cover, from get_candidate/cited filings. " +
                        "Write the reinvestment-runway rationale: is there a credible, evidenced case (capex plans, TAM commentary, management statements) for why the price is justified by the runway to keep reinvesting at high returns? " +
                        "Ground this in cited evidence, not generic optimism. Close with Terry Smith's own discipline: what specific evidence would impair the thesis (feeds §10 Kill Triggers) — 'do nothing' means not selling absent thesis impairment, not absolute inertia.",
                    canslim_notes:
                        "Write dossier §24 — CANSLIM Momentum Screen Notes (William O'Neil) — Track B only. This answers 'is it ready to buy now,' not 'is it a good business' " +
                        "(the fundamental screens already answered that) — you are the timing layer applied after those pass. " +
                        "Report current-quarter EPS growth (>=25% YoY, accelerating preferred) and 3-year EPS CAGR (>=25% with ROE >=17%) from get_candidate. " +
                        "Price/volume/relative-strength/institutional-ownership/market-direction data is NOT available through your current tools — state this plainly; do not fabricate a chart pattern, an RS-Rating percentile, a breakout-volume ratio, or a market-direction call. " +
                        "Define the momentum-breakdown condition that should feed future monitoring (e.g. 'breaks below the 50-day moving average on above-average volume') as a forward-looking rule.",
                };

                const sectionJobs = [
                    { key: "moat_understandability_gate", agent: "artha-moat-understandability", label: "section-15" },
                    { key: "qglp_scorecard", agent: "artha-qglp-scorer", label: "section-16" },
                    { key: "margin_of_safety_scuttlebutt", agent: "artha-margin-of-safety-scuttlebutt", label: "section-17" },
                    { key: "integrity_gate", agent: "artha-integrity-gate", label: "section-18" },
                    { key: "scale_economies_shared", agent: "artha-scale-economies-shared", label: "section-20" },
                    { key: "magic_formula_attribution", agent: "artha-magic-formula-attribution", label: "section-21" },
                    { key: "conviction_sizing", agent: "artha-conviction-sizing", label: "section-23" },
                ];
                if (track === "B") {
                    sectionJobs.push({ key: "davis_double_play", agent: "artha-davis-double-play", label: "section-19" });
                    sectionJobs.push({ key: "canslim_notes", agent: "artha-canslim-momentum", label: "section-24" });
                }
                if (track === "A") {
                    sectionJobs.push({ key: "quality_compounding_checklist", agent: "artha-quality-compounding", label: "section-22" });
                }

                const sectionResults = await ctx.parallel(
                    sectionJobs.map((job) => async () => {
                        const result = await ctx.agent(
                            `${FRAMEWORK_INSTRUCTIONS[job.key]}\n\n` +
                                `Ticker=${ctx.args.ticker}, snapshot_id=${ctx.args.snapshot_id}, track=${track}. ` +
                                `Candidate Stage 1a fields (from get_candidate): ${JSON.stringify(candidate.fields)}. ` +
                                `Call list_candidate_chunks/get_filing_chunk for every citation — never state a fact you cannot cite. ` +
                                `Return exactly the JSON shape your schema requires.`,
                            { agent: job.agent, label: job.label, schema: FRAMEWORK_SECTION_SCHEMAS[job.key] }
                        );
                        return { key: job.key, result };
                    })
                );

                const failedSections = sectionResults.filter((r) => r === null || r.result == null).map((r) => (r ? r.key : "unknown"));
                if (failedSections.length > 0) {
                    ctx.log(`framework subagent(s) produced no usable output: ${failedSections.join(", ")}`);
                }

                ctx.phase("Citation verification");
                // Adversarial verify: a distinct-lens subagent re-checks each
                // section's cited chunks actually support its claims — the
                // pattern implementation_plan.md §4 names, reducing but not
                // eliminating hallucination risk. The deterministic
                // validate_dossier gate below remains the non-negotiable
                // backstop regardless of this pass's outcome.
                const verified = await ctx.parallel(
                    sectionResults
                        .filter((r) => r !== null && r.result != null)
                        .map((r) => async () => {
                            const verdict = await ctx.agent(
                                `Adversarially verify every citation in this dossier section actually supports its claim: ${JSON.stringify(r.result)}`,
                                { agent: "artha-citation-verifier", label: `verify-${r.key}`, schema: CITATION_VERIFICATION_SCHEMA }
                            );
                            return { key: r.key, result: r.result, verification: verdict };
                        })
                );

                const sectionMap = {};
                for (const v of verified) {
                    if (v === null) continue;
                    sectionMap[v.key] = v.result;
                    if (v.verification && v.verification.all_citations_verified === false) {
                        ctx.log(`citation verification flagged unsupported claims in ${v.key}: ${JSON.stringify(v.verification.unsupported_claims)}`);
                    }
                }

                // Fail closed: a dossier missing one of its framework
                // sections is not assembled at all, rather than written
                // with a silently blank section (implementation_plan.md §8).
                const missingFrameworkSections = sectionJobs.map((j) => j.key).filter((key) => sectionMap[key] === undefined);
                if (missingFrameworkSections.length > 0) {
                    ctx.log(`aborting before assembly — missing framework sections: ${missingFrameworkSections.join(", ")}`);
                    return { error: "framework_sections_incomplete", missing: missingFrameworkSections };
                }

                ctx.phase("Assemble & validate");
                // The narrative/assembly agent (.github/agents/artha-dossier-narrative.md)
                // writes sections 1-14 given the completed framework-section
                // outputs as context. It is told to copy identity's stable
                // fields verbatim, but the factory still overrides them from
                // ctx.args/candidate below rather than trusting the
                // transcription — identity must never be guessed or drift.
                const today = new Date().toISOString().slice(0, 10);
                const narrative = await ctx.step("narrative-v2", () =>
                    ctx.agent(
                        `Write dossier sections 1-14 for ticker=${ctx.args.ticker}, snapshot_id=${ctx.args.snapshot_id}, track=${track}, ` +
                            `pipeline_run_id=${ctx.runId}, date=${today}, arithmetic_profile=${candidate.arithmetic_profile}. ` +
                            `Candidate Stage 1a fields: ${JSON.stringify(candidate.fields)}. ` +
                            `Completed framework-section outputs (§15-24), for consistency (e.g. fatal_flaw_checklist should ` +
                            `reference the integrity_gate/moat_understandability_gate flags, buy_below_and_sizing should be ` +
                            `informed by conviction_sizing's proposed size): ${JSON.stringify(sectionMap)}. ` +
                            `Set identity.ticker, identity.snapshot_id, identity.track, identity.arithmetic_profile, and ` +
                            `identity.pipeline_run_id to exactly the values given above. Research identity.company and ` +
                            `identity.sector using get_filing_chunk/list_candidate_chunks/get_candidate — never guess them.`,
                        { agent: "artha-dossier-narrative", label: "narrative-assembly", schema: NARRATIVE_SCHEMA }
                    )
                );

                if (!narrative) {
                    ctx.log("narrative/assembly subagent failed or returned no parseable output — aborting before write");
                    return { error: "narrative_assembly_failed" };
                }

                // Deterministic merge: identity's stable fields and every
                // framework-section output come from code/verified subagent
                // results, not from the narrative agent's own transcription
                // of them (implementation_plan.md §4/§6).
                const draft = {
                    ...narrative,
                    identity: {
                        ...narrative.identity,
                        ticker: ctx.args.ticker,
                        snapshot_id: ctx.args.snapshot_id,
                        track,
                        arithmetic_profile: candidate.arithmetic_profile,
                        pipeline_run_id: ctx.runId,
                    },
                    ...sectionMap,
                };

                ctx.phase("Write");
                // write-dossier is the factory's own write step — server-
                // side orchestration code calling the Python CLI directly,
                // not an agent-callable tool (no research agent is ever one
                // tool-call away from a write path, per §7's safety rule).
                // It validates internally (writing the file + index row
                // even on failure, with stage="rejected") and journals the
                // decision, so one call here covers assemble+validate+write.
                const write = await ctx.step("write-v2", async () => {
                    const { exitCode, stdout, stderr } = await runArthaCli(
                        ["write-dossier", "--run-id", ctx.runId, "--factory-run-id", ctx.runId, "--model", "github-copilot-agent-factory:artha-dossier"],
                        { stdin: JSON.stringify(draft) }
                    );
                    try {
                        return { exitCode, data: JSON.parse(stdout) };
                    } catch {
                        return { exitCode, data: { error: stderr || stdout || `write-dossier exited ${exitCode} with no output` } };
                    }
                });

                ctx.log(
                    `artha-dossier run ${ctx.runId} for ${ctx.args.ticker}: ` +
                        (write.data.error ? `write failed — ${write.data.error}` : `wrote ${write.data.file_path}, validation_passed=${write.data.validation_passed}`)
                );

                return {
                    ticker: ctx.args.ticker,
                    track,
                    run_id: ctx.runId,
                    write: write.data,
                    citation_verification: verified.map((v) => (v ? { key: v.key, verification: v.verification } : null)),
                };
            },
        }),
    ],
});
