# Artha

Wealth pursued through sound, disciplined means.

Artha is a local, single-user research and execution pipeline for Indian
equities. It turns a Screener.in CSV export into a ranked, rule-attributed
shortlist, drives an evidence-cited deep-dive dossier per candidate, and keeps
a post-tax paper ledger scored against a benchmark you froze before you
started.

Everything runs on your machine. There is no server, no account, and no network
dependency except the exports and filings you feed it yourself. State lives in
one SQLite file plus a directory of markdown dossiers.

The full specification is [`plan.md`](plan.md); the build sequence and
architecture are in [`implementation_plan.md`](implementation_plan.md). This
README is the operating manual.

---

## What it does

```text
Screener CSV ──► artha data import-screener ──► immutable, hashed snapshot
                                                        │
                        ┌───────────────────────────────┴──────────────┐
                        ▼                                              ▼
              artha rank (engine)                            artha screen (v1)
       expected post-tax CAGR, ranked                 pass/fail Stage 1+2 rules
                        │
                        ▼
      artha research <ticker> ──► 24-section dossier, every claim cited
                        │
                        ▼
      artha ledger buy/sell ──► FIFO tax lots, post-tax scorecard vs benchmark
```

Four ideas the design is built around:

**Never silently guess.** Every candidate lands in exactly one of three
buckets — ranked, rejected by a named rule, or blocked by missing data. A
zero-length shortlist always tells you which of the two it was. Missing data is
never treated as a pass or a fail.

**Reproducible by construction.** Snapshots are content-addressed and hashed.
Every coefficient the ranking engine uses lives in
[`config/formula.toml`](config/formula.toml), and every run records that file's
sha256 fingerprint. A ranking from six months ago can be re-derived exactly.

**Cite or it didn't happen.** Dossiers are rejected, not warned about, when a
claim has no `(doc_id, page)` citation into an ingested filing. The LLM agents
that write them can only read from a four-tool, read-only surface.

**Post-tax or it's fiction.** Returns are taxed at the terminal gain and
re-annualised (STCG 20% held ≤12 months, LTCG 12.5% beyond, ₹1.25L annual
exemption). The scorecard compares post-tax, money-weighted returns to the two
components of your frozen benchmark, judged independently.

---

## Install

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"

# Config templates — the copies are gitignored, fill in your real values:
Copy-Item config\artha.example.toml config\artha.toml
Copy-Item config\screener_field_map.example.toml config\screener_field_map.toml
Copy-Item config\ips.template.md config\ips.md

.venv\Scripts\artha --version
.venv\Scripts\artha init          # creates .artha/artha.db, applies migrations
.venv\Scripts\artha config show   # prints the resolved, validated config
```

Requires Python ≥3.11. Runtime dependencies are `click` and `keyring` only —
all numerics are stdlib.

Write and freeze your IPS (`config/ips.md`) and your benchmark
(`config/artha.toml`'s `[benchmark]`) **before** funding anything. The sell
discipline and the scorecard both read from them, and freezing after the fact
defeats the purpose.

---

## The commands

All examples below assume `.venv\Scripts\` is on your path; if not, prefix them
with it.

### `artha init` / `artha config show`

Bootstrap the database and print the resolved config. `init` is idempotent and
safe to re-run — it applies any pending schema migrations.

### `artha data ...` — the data spine

```powershell
# Ingest a Screener export; runs the plan.md §13.4 validation-spike checks
artha data import-screener screener_exports\my-export.csv `
    --source screener_profile1 --profile profile_1_standard

artha data show-snapshot <snapshot_id>      # metadata + per-field completeness
artha data check-staleness <snapshot_id>    # §13.6 staleness guard

# Filings: the citation-preserving chunk store dossiers cite into
artha data import-filing filings\alpha_q1fy25.txt --doc-id ALPHA_Q1FY25 --ticker ALPHA
artha data show-chunk ALPHA_Q1FY25 1        # print one (doc_id, page) chunk
```

`--source` is a label you choose and reuse; `screen` and `rank` resolve the
latest snapshot for that label. `--profile` selects the §5.3a arithmetic
profile — `profile_1_standard` for operating companies, `profile_2_banking` for
lenders, where ratios like EV/EBIT are meaningless.

Column names differ between Screener exports. Map yours in
`config/screener_field_map.toml`; unmapped fields report as missing rather than
being guessed at.

### `artha rank` — the ranking engine

Ranks a snapshot by expected post-tax CAGR. This is the primary path.

```powershell
artha rank --source screener_profile1 --track A --top 25
artha rank --source screener_profile1 --track A --explain   # + feature coverage
artha rank --source screener_profile2_financial_services --profile profile_2_banking --track B
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--source` | *required* | Snapshot source label from `import-screener` |
| `--track` | *required* | `A` (compounders, 5y) or `B` (asymmetry, 3y) |
| `--profile` | `profile_1_standard` | §5.3a arithmetic profile |
| `--formula` | `config/formula.toml` | Coefficient spec to run under |
| `--top` | `25` | How many ranked names to print |
| `--explain` | off | Print feature coverage across the universe |

Output is a header with the four bucket counts, the formula version and
fingerprint, the ranked names, then a tally of rejections by rule and of what
blocked the rest:

```text
universe: 1104  ranked: 727  rejected: 209  insufficient data: 168
formula: v1 (b217b85e0199e3cf)  snapshot: 3f2a91c0de44

top 25 by expected post-tax CAGR weighted by evidence confidence:
    1. EXAMPLE LTD                  net   31.4%  gross   35.9%  confidence   82%
```

Names are sorted by `net_cagr × confidence`, so a thinly-evidenced 40% ranks
below a well-evidenced 30%. A `*` marks a name carrying an unresolved Stage 1b
check — it is ranked, but not buyable until that is answered.

Change any number in `config/formula.toml` and the fingerprint changes. That is
deliberate: no ranking can be quietly re-attributed to different coefficients
after the fact.

### `artha screen` — the v1 rule screen

The original pass/fail Stage 1+2 pipeline (Agrawal QGLP, Graham defensive,
Buffett-Munger/Terry Smith moat refinement, Lynch PEG, Davis, Kedia SMILE,
O'Neil CANSLIM, plus the Greenblatt Magic Formula and Pabrai asymmetry hard
blocks). It runs alongside `rank` and attributes every exclusion to the exact
rule that fired.

```powershell
artha screen --source screener_profile1 --track A
```

Use `rank` to decide what to research, and `screen` to ask "which specific
rules would this name have failed."

Every run is persisted to a queryable `screen_results` table (not just
printed and journaled) — list past runs or re-list a shortlist without
re-running the screen:

```powershell
artha screen-results list-runs
artha screen-results show <screen_run_id> --status shortlisted
artha screen-results show <screen_run_id> --status excluded
artha screen-results show <screen_run_id> --status pending
```

Checks the plan itself assigns to Stage 1b (multi-year own-history: sustained
10-year ROE/ROIC, the 10-year earnings-deficit record, Davis's own-5-year P/E
tercile) or Stage 3 (qualitative judgment: scuttlebutt, business
explainability, promoter aspiration) are reported as `needs_stage_1b` /
`needs_stage_3`, never guessed at.

### `artha research <ticker>` — dossier generation

Fans out one subagent per dossier framework section, runs an adversarial
citation-verification pass, then assembles and validates against the 24-section
schema. **Phase 3 — the harness is built and verified, but the end-to-end run
is not yet wired to this command, which currently refuses to run.** Today you
drive the factory through Copilot, or call the tool surface directly:

```powershell
artha agent-tools get-candidate ALPHA --source screener_profile1
artha agent-tools get-filing-chunk ALPHA_Q1FY25 1
artha agent-tools list-candidate-chunks ALPHA --topic pledge
Get-Content draft.json | artha agent-tools validate-dossier
Get-Content draft.json | artha agent-tools write-dossier --run-id run-001
```

The first four are read-only and are exactly what the agents can call. The
write step is orchestration code, never an agent-callable tool.

The validator rejects rather than warns: a missing section, empty disconfirming
evidence, empty provenance, an uncited evidence claim, a failed gate, or a
track-conditional section in the wrong state all fail the write.

### `artha ledger ...` — positions, tax, scorecard

```powershell
artha ledger buy ALPHA --track A --quantity 100 --price 500 --trade-date 2025-01-15
artha ledger sell ALPHA --quantity 40 --price 650 --trade-date 2026-03-01
artha ledger positions --track A

# Frozen-benchmark NAV, one point at a time. Fund names must match
# config/artha.toml's [benchmark] exactly.
artha ledger import-benchmark-nav --fund-name "<index fund>" --nav-date 2026-03-01 --nav 275.0

artha ledger scorecard --track A --as-of-date 2026-03-01 --price ALPHA=650
```

`--price TICKER=PRICE` is repeatable and supplies the current mark for each
open position; there is no live price feed.

Selling a tax lot held under 12 months raises `SellDisciplineError` unless you
pass `--override-reason`. That is `config/ips.md` §5 enforced in code rather
than left to your memory at the moment it is least reliable.

### `artha secrets ...`

```powershell
artha secrets set kite_api_key      # prompts, writes to the OS keyring
artha secrets get kite_api_key      # reports set / not-set, never the value
artha secrets delete kite_api_key
```

Credentials go in the OS keyring. Never in the repo, never in an env file.

### `artha review` / `artha order`

Documented stubs that refuse to run — Gate 1 thesis approval and Phase 6 Kite
execution.

---

## Where outputs go

| What | Where | Committed? |
| --- | --- | --- |
| Database — snapshots, filings, tax lots, journal, dossier index | `.artha/artha.db` | No, gitignored |
| Rendered dossiers | `dossiers/<ticker>/<run_id>.md` | Immutable; a new run needs a new `run_id` |
| Screener exports you ingest | `screener_exports/` | Your call |
| Resolved config | `config/artha.toml`, `config/screener_field_map.toml` | No, gitignored — the `.example` files are committed |
| Frozen IPS | `config/ips.md` | No, gitignored — `ips.template.md` is committed |
| Formula coefficients | `config/formula.toml` | **Yes** — fingerprinted into every run |
| `rank` / `screen` results | stdout, plus a journal row in the database | — |

Snapshot CSV bytes are stored content-addressed, so the same export ingested
twice is stored once, and a run always reproduces from the exact bytes it saw.

**The journal.** Every `screen` run, `rank` run, ledger trade, and dossier write
appends a hash-chained entry. Each row hashes the previous row's hash, so
retroactively editing history breaks the chain verifiably. Read it via
`artha.journal.Journal(conn).all_entries()`; check integrity with
`verify_chain()`.

**Dossiers are immutable.** `write_dossier` refuses to overwrite an existing
`<run_id>.md`. Regenerate under a new run id; the old one stays as the record
of what you actually believed at the time.

---

## Reading `rank` output honestly

Standing caveats, kept here rather than buried:

- **The ordering is meaningful; the magnitudes are not calibrated.** Top names
  sit near the model's term bounds, growth leans on 3-year figures that can
  reflect recovery from a low base, and the default probability model in
  `config/formula.toml` is uncalibrated. Treat the output as "research these
  first," not "expect 31%."
- **Cash conversion is not screened.** Screener cannot export OCF/PAT and it is
  not reconstructable from what it does export, so the field was removed
  entirely rather than faked. Verifying that reported profit becomes cash is a
  Stage 3 filing-review item, read from the cash flow statement and cited.
- **Lender quality is thin.** For `profile_2_banking`, valuation correctly
  substitutes earnings yield (PAT/MarketCap) for EV/EBIT, but the quality score
  still leans on ratios that mean less for a bank. ROA, NIM, GNPA, and CAR are
  absent from Screener exports. Treat banking rankings as indicative.
- **`--explain` is the honest first stop.** If a bucket looks wrong, feature
  coverage usually explains it before the formula does.

---

## Tests

```powershell
.venv\Scripts\pytest -q
```

283 tests. The tax, scorecard, and tax-lot suites include hand-computed
reconciliation tests, so if the arithmetic drifts those fail rather than the
numbers quietly changing.

---

## Build status

| Phase | State |
| --- | --- |
| 0 — foundations: config, DB, journal, keyring, CLI | Complete |
| 1 — data spine: snapshots, staleness guard, filing chunks | Complete |
| 2 — screening + hard blocks, and the `rank` engine rebuild | Complete |
| 2.5 — dossier schema, validator, renderer, storage | Complete |
| 3a — agent harness: extension, agents, skills, factory | Complete |
| 3 — real dossiers generated end to end | 5 dossiers produced manually via the harness; factory fan-out not yet unattended |
| 4 — paper ledger + scorecard | Built; ongoing data entry |
| 5-6 — monitoring, Kite execution | Not started |

Open engine work: making `quality_score` profile-aware for lenders, and
calibrating the formula coefficients against point-in-time history — the
walk-forward harness in `artha/backtest/` is built and waiting on data.

**Milestone:** one real, fully-cited dossier has been produced end-to-end —
**Eco Recycling Limited** (NSE: ECORECO), Track A —
[`dossiers/Eco Recyc/run-ecoreco-20260830-001.md`](<dossiers/Eco Recyc/run-ecoreco-20260830-001.md>).
Both gates passed honestly and the QGLP score (6/12) correctly reflects a
statistically expensive stock with real, unresolved diligence gaps rather
than an inflated buy case. It was assembled by manually following each
`.github/agents/*.md` role in turn — the factory's own fan-out
(`run_factory("artha-dossier")`) is registered but not yet fully wired for
an unattended end-to-end run. Four more dossiers exist alongside it in
`dossiers/`. The run surfaced and fixed two real bugs: `agent-tools`
commands decoded stdin with the platform default encoding instead of UTF-8
(mojibake on Windows for any non-ASCII citation text), and ticker names
ending in a period (e.g. "Eco Recyc.") silently lost that period in the
dossier directory path on Windows. Both have regression tests.

Detailed per-phase exit criteria live in [`plan.md`](plan.md) §11 and
[`implementation_plan.md`](implementation_plan.md) §3. Phase 1's empirical
validation results are recorded in
[`docs/phase1_validation_spike.md`](docs/phase1_validation_spike.md).
