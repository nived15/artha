# Artha

Wealth pursued through sound, disciplined means.

See [`plan.md`](plan.md) for the full specification and
[`implementation_plan.md`](implementation_plan.md) for the build sequence and
architecture. This README covers Phases 0-4.

## Phase 0 — foundations

What exists so far: repo skeleton, config schema/loader, SQLite schema +
migrations, an append-only tamper-evident journal, an OS-keyring secrets
wrapper, and the `artha` CLI shell (`artha --version`, `artha init`,
`artha config show`, `artha secrets ...`). Screening, dossiers, the ledger,
monitoring, and execution are later phases — the corresponding CLI
subcommands (`research`, `review`, `order`) are present as documented
stubs that refuse to run until their phase lands.

## Phase 1 — data spine

Content-addressable snapshot store for Screener.in CSV exports, the §13.4
validation-spike checks, a staleness guard (§13.6), and a citation-preserving
(doc_id, page, text) chunk store for filings. See
[`docs/phase1_validation_spike.md`](docs/phase1_validation_spike.md) for the
desk-research results — the empirical parts of the spike (smallcap
completeness, full column-ceiling/sector-field confirmation) require an
actual Screener Premium export, which only you can produce.

```powershell
# Fill in real Screener column names once you have an export (desk-research
# starting point in config/screener_field_map.example.toml):
Copy-Item config\screener_field_map.example.toml config\screener_field_map.toml

# Ingest a real export and run the §13.4 spike checks against it:
.venv\Scripts\artha data import-screener path\to\export.csv --source screener_profile1 --profile profile_1_standard

.venv\Scripts\artha data show-snapshot <snapshot_id>
.venv\Scripts\artha data check-staleness <snapshot_id>

# Filings: citation-preserving chunk store
.venv\Scripts\artha data import-filing path\to\filing.txt --doc-id ALPHA_Q1FY25 --ticker ALPHA
.venv\Scripts\artha data show-chunk ALPHA_Q1FY25 1
```

## Phase 2 — screening + hard blocks

Deterministic Track A/B Stage 1 screens (Agrawal QGLP, Buffett & Munger/
Terry Smith moat refinement, Graham defensive criteria, Lynch PEG, Davis
Double Play, Kedia SMILE, O'Neil CANSLIM overlay) and Stage 2 fatal-flaw
hard blocks (promoter pledging/integrity, the Greenblatt Magic Formula
ranking gate, the Pabrai asymmetry gate). Every exclusion is attributed to
the exact rule that fired; every gap in Stage 1a data is reported as
"pending" rather than silently assumed.

**Scope boundary, per plan.md §13's own Stage 1a/1b split:** only checks
computable from a single snapshot row are automated here. Checks the plan
itself assigns to Stage 1b (multi-year own-history: sustained 10-year
ROE/ROIC, 10-year earnings-deficit/dividend record, Davis's own-5-year P/E
tercile) or Stage 3 (qualitative LLM judgment: scuttlebutt, business
explainability, promoter aspiration) are reported as `needs_stage_1b` /
`needs_stage_3`, never guessed at.

```powershell
.venv\Scripts\artha screen --source screener_profile1 --track A
.venv\Scripts\artha screen --source screener_profile1 --track B
```

## Phase 2.5 — dossier schema + validator

The 24-section dossier data model (`artha/dossier/schema.py`), a
completeness + citation-presence validator that rejects rather than warns
(`artha/dossier/validator.py`), a markdown renderer matching plan.md §6's
section layout, and storage that writes the immutable markdown artifact
to `dossiers/<ticker>/<run_id>.md` plus a queryable SQLite index row
(implementation_plan.md §16 Q1). This is a library only — no LLM
dependency, no CLI wiring yet. Phase 3a's agent harness and Phase 3's
factory will be the first callers, writing into this exact contract:

```python
from artha.dossier.storage import write_dossier
from artha.dossier.validator import validate_dossier

result = write_dossier(conn, dossier, run_id="run-001")
result.validation.passed   # False rejects, listing every defect by section
```

Sections 12 (disconfirming evidence) and 14 (provenance) are checked as
the plan's own "anti-self-deception mechanism"; the two gate sections (15
moat/understandability, 18 integrity) are checked as gates, not just
evidence — a `passed=False` gate is itself a validation error, distinct
from a missing/incomplete section. Track-conditional sections (19 Davis,
22 Terry Smith, 24 CANSLIM) are typed `X | None` so "not applicable to
this track" and "applicable but missing" are never conflated.

## Phase 3a — agent harness (extension, agents, skills, factory)

The Copilot-facing machinery that will generate real dossiers in Phase 3:

- **`.github/extensions/artha-tools/`** — a project extension exposing four
  read-only tools (`get_filing_chunk`, `get_candidate`,
  `list_candidate_chunks`, `validate_dossier`) that shell out to new
  `artha agent-tools ...` CLI commands (JSON in/out). No write/order tools
  live here — the factory's own write step is server-side orchestration
  code, never an agent-callable tool.
- **`.github/agents/`** — one custom agent per dossier framework section
  (§15 moat/understandability gate through §24 CANSLIM), plus a citation
  verifier (adversarial re-check of every cited claim) and a
  narrative/assembly agent (§1-14 + final JSON merge). Each is restricted
  to the four read-only tools above and instructed to cite every claim.
- **`.github/skills/`** — reusable, versioned procedures the agents share:
  citation discipline, the ROIIC calculation, the QGLP 0-3 scoring rubric,
  the 7-gate understandability checklist, and the exact dossier JSON
  schema `validate_dossier` expects.
- **The `artha-dossier` factory** (registered by the extension via
  `defineFactory`) — `args: {ticker, snapshot_id, track}`, fans out one
  subagent per framework section, runs the adversarial citation-verify
  pass, then assembles. Limits match `BudgetConfig`'s defaults
  (`maxConcurrentSubagents: 5`, `maxTotalSubagents: 20`, `maxAiCredits: 5`,
  `timeoutSeconds: 3600`).

```powershell
# The read-only tool surface, callable directly for testing:
.venv\Scripts\artha agent-tools get-candidate ALPHA --snapshot-id <id>
.venv\Scripts\artha agent-tools get-filing-chunk ALPHA_Q1FY25 1
.venv\Scripts\artha agent-tools list-candidate-chunks ALPHA --topic pledge
echo '{"identity": {...}, ...}' | .venv\Scripts\artha agent-tools validate-dossier
echo '{"identity": {...}, ...}' | .venv\Scripts\artha agent-tools write-dossier --run-id run-001
```

**Scope boundary:** Phase 3a builds and verifies the harness — the
extension loads, all four tools work end-to-end (verified against the
running Copilot session, not just pytest), and the factory registers with
the correct argument schema and limits. It deliberately does **not** run a
real dossier generation end to end — that is Phase 3's exit criterion
("20+ dossiers that pass their own completeness checks"), and running the
full fan-out for real spends real AI credits across ~12 subagent calls per
dossier, which belongs to a phase whose job is producing real dossiers, not
building the plumbing.

## Phase 4 — paper ledger + scorecard

A FIFO tax-lot engine (`artha/ledger/tax_lots.py`), post-July-2024 Indian
capital-gains tax (`artha/ledger/tax.py`: STCG 20% held ≤12 months, LTCG
12.5% held longer, ₹1.25L annual LTCG exemption, standard loss set-off
rules), position aggregation with an accrued-tax-on-unrealized-gains
estimate (`artha/ledger/positions.py`), and the per-track, post-tax,
money-weighted scorecard against the frozen benchmark's two components,
judged independently (`artha/ledger/scorecard.py`) — plan.md §9 and §11.

**Sell discipline is enforced, not just documented:** `artha ledger sell`
refuses to touch any tax lot held under 12 months unless you pass
`--override-reason`, matching config/ips.md §5's own rule literally rather
than trusting you to remember it.

```powershell
.venv\Scripts\artha ledger buy ALPHA --track A --quantity 100 --price 500 --trade-date 2025-01-15
.venv\Scripts\artha ledger sell ALPHA --quantity 40 --price 650 --trade-date 2026-03-01
.venv\Scripts\artha ledger positions --track A

# Frozen-benchmark NAV history, one point at a time (fund names must match
# config/artha.toml's [benchmark] exactly):
.venv\Scripts\artha ledger import-benchmark-nav --fund-name "<index fund>" --nav-date 2025-01-15 --nav 250.0
.venv\Scripts\artha ledger import-benchmark-nav --fund-name "<index fund>" --nav-date 2026-03-01 --nav 275.0

.venv\Scripts\artha ledger scorecard --track A --as-of-date 2026-03-01 --price ALPHA=650
```

**Honest simplifications, carried forward from `artha/ledger/scorecard.py`'s
own docstring:** `time_weighted_return` needs periodic valuation marks
supplied by the caller (there's no live price feed to derive them from
automatically) — expose it as a reusable function, don't try to auto-derive
it from trades alone. Post-tax XIRR applies each fiscal year's realized
capital-gains tax as one lump-sum outflow at the valuation date rather than
modeling the exact ITR payment date. Loss carry-forward across fiscal years
is not modeled yet — revisit if the paper record shows it matters.

### Setup

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"

# Copy the config templates and fill in your real values (gitignored):
Copy-Item config\artha.example.toml config\artha.toml
Copy-Item config\screener_field_map.example.toml config\screener_field_map.toml

# Write and freeze your IPS from the template before funding anything:
Copy-Item config\ips.template.md config\ips.md

.venv\Scripts\artha --version
.venv\Scripts\artha init            # creates .artha/artha.db and applies migrations
.venv\Scripts\artha config show     # prints the resolved, validated config
```

### Tests

```powershell
.venv\Scripts\pytest -q
```

### Phase 0 exit criteria (plan.md §11)

- [x] IPS written and frozen (`config/ips.md`, frozen 2026-08-29)
- [x] Benchmark frozen and recorded (`config/artha.toml`'s `[benchmark]` section:
      70% UTI Nifty 50 Index Fund / 30% Motilal Oswal Nifty 200 Momentum 30
      Index Fund, frozen 2026-08-29)
- [x] Passive core and ballast funded (2026-08-29, per `config/ips.md` §2 —
      manual brokerage action, outside this repo)
- [x] Repo skeleton, SQLite schema, config, secrets in keyring
- [x] `artha --version` runs

### Phase 1 exit criteria (plan.md §11)

- [x] Content-addressable, hashed snapshot store; a screen run reproduces
      exactly from a stored snapshot
- [x] Staleness guard refuses to build on a snapshot older than
      `data.snapshot_max_age_days`
- [x] Citation-preserving (doc_id, page, chunk_index) filing chunk store
- [x] §13.4 desk-research recorded (`docs/phase1_validation_spike.md`)
- [x] §13.4 empirical checks — confirmed 2026-08-30 against real Screener
      Premium exports (`screener_exports/artha-profile-1-validation.csv`,
      1104 smallcap rows, `screener_exports/financial-services.csv`, 654
      rows). Column ceiling, shareholding fields, and smallcap completeness
      all pass for Profile 1; banking/insurance sector fields confirmed
      absent, moving Profiles 2/3 to Stage 1b. See
      `docs/phase1_validation_spike.md`.

### Phase 2 exit criteria (plan.md §11)

- [x] Both track screens (QGLP, Graham, Terry Smith/Buffett-Munger moat
      refinement, Davis, Lynch PEG, Kedia SMILE, O'Neil CANSLIM) and the
      Greenblatt/Pabrai hard blocks implemented, deterministic, unit-tested
- [x] `artha screen` produces a ranked shortlist per track, with every
      exclusion attributed to the exact rule that fired — verified against
      the real 1104-row Profile 1 snapshot above (Track A: 0 shortlisted,
      909 excluded, 195 pending Stage 1b data; Track B: 0 shortlisted, 1104
      excluded by the Greenblatt/Pabrai hard blocks)
- [x] Phase 2 field-map columns (`current_ratio`, `price_to_book`,
      `profit_growth_5y`, `eps_growth_ttm_yoy`, `eps_growth_latest_q_yoy`,
      `interest_coverage`, `fcf_conversion_pct`, `dividend_yield_pct`,
      `sector`) confirmed against a real 654-row export
      (`screener_exports/financial-services.csv`, 2026-08-30) at 72.8-100%
      completeness; verified end-to-end via `artha agent-tools
      get-candidate` and re-running `artha screen` against it. Four fields
      remain genuinely unconfirmed and stay `<TODO>` rather than being
      guessed at: `ocf_to_pat` and `gross_margin` (no matching native or
      derivable column), `years_since_incorporation` (not a Screener
      field), and `analyst_coverage_count` (the export's own `Expected
      quarterly EPS` sparsity is the low-coverage signal per plan.md
      §13.3b, but its value is an EPS estimate, not a count, so it can't
      be mapped directly without corrupting the `<= 2` threshold check in
      `track_b.py`)

### Phase 2.5 exit criteria (implementation_plan.md §3)

- [x] Dossier schema covers all 24 mandatory sections plus the two gates
- [x] Validator rejects (never warns) on missing sections, empty
      disconfirming-evidence/provenance, missing citations on evidence
      sections, a failed gate, or a track-conditional section in the
      wrong state
- [x] Storage writes the immutable markdown file + SQLite index row,
      matching implementation_plan.md §16 Q1's "both" resolution
- [ ] First real dossier generated end-to-end (Phase 3 — needs Phase 3a's
      agent harness)

### Phase 3a exit criteria (implementation_plan.md §3-§4)

- [x] Project extension exposes the read-only tool surface
      (`get_filing_chunk`, `get_candidate`, `list_candidate_chunks`,
      `validate_dossier`); verified loading cleanly and each tool working
      end-to-end against real ingested test data
- [x] One custom agent per framework section (§15-24) plus a citation
      verifier and a narrative/assembly agent, each restricted to the
      read-only tool surface
- [x] Skills for the shared, reusable procedures (citation discipline,
      ROIIC, QGLP rubric, understandability checklist, dossier JSON schema)
- [x] `artha-dossier` factory registered with a declared `argsSchema` and
      limits matching `BudgetConfig`'s defaults; verified via
      `factories_manage inspect`
- [ ] Full end-to-end dossier generation (Phase 3 — this phase builds the
      harness, Phase 3 runs it for real candidates)

### Phase 4 exit criteria (plan.md §11)

- [x] Paper positions (`artha/ledger/positions.py`), FIFO tax lots
      (`artha/ledger/tax_lots.py`), and time/money-weighted post-tax
      performance vs. the frozen benchmark, per track
      (`artha/ledger/scorecard.py`)
- [x] Sell discipline enforced: selling a lot held <12 months raises
      `SellDisciplineError` unless `--override-reason` is given
      (config/ips.md §5)
- [x] **Gets real tests**: `tests/test_tax_lots.py`, `test_tax.py`,
      `test_positions.py`, `test_scorecard.py` — 39 tests total
- [x] Scorecard reconciles against a hand-computed example
      (`test_xirr_single_buy_single_sale_reconciles_by_hand`,
      `test_time_weighted_return_reconciles_by_hand`,
      `test_track_scorecard_reconciles_by_hand`)
- [ ] Real trades entered as they happen (`artha ledger buy`/`sell`) and
      benchmark NAV tracked over time (`artha ledger import-benchmark-nav`)
      — this is ongoing, human-driven data entry, not a one-time build step

### Credentials

Never put credentials in the repo or in env files. Store them in the OS
keyring:

```powershell
.venv\Scripts\artha secrets set kite_api_key
.venv\Scripts\artha secrets get kite_api_key   # reports set/not-set only
```
