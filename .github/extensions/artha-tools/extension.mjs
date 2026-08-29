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
                // sections 15-24), each restricted (by the calling agent
                // definitions in .github/agents/) to this extension's
                // read-only tools and required to cite (doc_id, page) for
                // every claim. Track-conditional sections are only fanned
                // out for their track.
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
                            `Research and write dossier section for ticker=${ctx.args.ticker}, snapshot_id=${ctx.args.snapshot_id}, track=${track}. ` +
                                `Candidate fields: ${JSON.stringify(candidate.fields)}. Use get_filing_chunk/list_candidate_chunks for every citation.`,
                            { agent: job.agent, label: job.label }
                        );
                        return { key: job.key, result };
                    })
                );

                ctx.phase("Citation verification");
                // Adversarial verify: a distinct-lens subagent re-checks each
                // section's cited chunks actually support its claims — the
                // pattern implementation_plan.md §4 names, reducing but not
                // eliminating hallucination risk. The deterministic
                // validate_dossier gate below remains the non-negotiable
                // backstop regardless of this pass's outcome.
                const verified = await ctx.parallel(
                    sectionResults
                        .filter((r) => r !== null)
                        .map((r) => async () => {
                            const verdict = await ctx.agent(
                                `Adversarially verify every citation in this dossier section actually supports its claim: ${JSON.stringify(r.result)}`,
                                { agent: "artha-citation-verifier", label: `verify-${r.key}` }
                            );
                            return { key: r.key, result: r.result, verification: verdict };
                        })
                );

                ctx.phase("Assemble & validate");
                // ctx.step("assemble", ...) calls the Python validate_dossier
                // tool before writing — the assembly step here is a
                // placeholder for Phase 3's real narrative-section agent
                // and JSON merge logic; Phase 3a's job is the harness, not
                // a finished end-to-end run (implementation_plan.md §3).
                const assembly = await ctx.step("assemble-v1", async () => ({
                    ticker: ctx.args.ticker,
                    snapshot_id: ctx.args.snapshot_id,
                    track,
                    sections: verified,
                }));

                ctx.log(`artha-dossier run ${ctx.runId} completed fan-out + verification for ${ctx.args.ticker}`);
                return assembly;
            },
        }),
    ],
});
