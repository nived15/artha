# Artha

Wealth pursued through sound, disciplined means.

See [`plan.md`](plan.md) for the full specification and
[`implementation_plan.md`](implementation_plan.md) for the build sequence and
architecture. This README covers Phases 0-1.

## Phase 0 — foundations

What exists so far: repo skeleton, config schema/loader, SQLite schema +
migrations, an append-only tamper-evident journal, an OS-keyring secrets
wrapper, and the `artha` CLI shell (`artha --version`, `artha init`,
`artha config show`, `artha secrets ...`). Screening, dossiers, the ledger,
monitoring, and execution are later phases — the corresponding CLI
subcommands (`screen`, `research`, `review`, `order`) are present as
documented stubs that refuse to run until their phase lands.

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

### Credentials

Never put credentials in the repo or in env files. Store them in the OS
keyring:

```powershell
.venv\Scripts\artha secrets set kite_api_key
.venv\Scripts\artha secrets get kite_api_key   # reports set/not-set only
```
