# Artha

Wealth pursued through sound, disciplined means.

See [`plan.md`](plan.md) for the full specification and
[`implementation_plan.md`](implementation_plan.md) for the build sequence and
architecture. This README covers Phases 0-2.

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

- [ ] IPS written and frozen (`config/ips.md`, human action — see the template)
- [ ] Benchmark frozen and recorded (`config/artha.toml`'s `[benchmark]` section)
- [ ] Passive core and ballast funded (manual brokerage action, outside this repo)
- [x] Repo skeleton, SQLite schema, config, secrets in keyring
- [x] `artha --version` runs

### Phase 1 exit criteria (plan.md §11)

- [x] Content-addressable, hashed snapshot store; a screen run reproduces
      exactly from a stored snapshot
- [x] Staleness guard refuses to build on a snapshot older than
      `data.snapshot_max_age_days`
- [x] Citation-preserving (doc_id, page, chunk_index) filing chunk store
- [x] §13.4 desk-research recorded (`docs/phase1_validation_spike.md`)
- [ ] §13.4 empirical checks — smallcap completeness, full column-ceiling
      confirmation (human action — needs a real Screener Premium export;
      run `artha data import-screener` once you have one)

### Phase 2 exit criteria (plan.md §11)

- [x] Both track screens (QGLP, Graham, Terry Smith/Buffett-Munger moat
      refinement, Davis, Lynch PEG, Kedia SMILE, O'Neil CANSLIM) and the
      Greenblatt/Pabrai hard blocks implemented, deterministic, unit-tested
- [x] `artha screen` produces a ranked shortlist per track, with every
      exclusion attributed to the exact rule that fired
- [ ] Fill in the remaining `config/screener_field_map.toml` Phase 2 fields
      (`ocf_to_pat`, `profit_growth_5y`, etc.) against a real export so the
      screens run on complete data rather than reporting "pending"

### Credentials

Never put credentials in the repo or in env files. Store them in the OS
keyring:

```powershell
.venv\Scripts\artha secrets set kite_api_key
.venv\Scripts\artha secrets get kite_api_key   # reports set/not-set only
```
