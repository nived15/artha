# Artha

Wealth pursued through sound, disciplined means.

See [`plan.md`](plan.md) for the full specification and
[`implementation_plan.md`](implementation_plan.md) for the build sequence and
architecture. This README covers Phase 0 setup only.

## Phase 0 — foundations (this checkout)

What exists so far: repo skeleton, config schema/loader, SQLite schema +
migrations, an append-only tamper-evident journal, an OS-keyring secrets
wrapper, and the `artha` CLI shell (`artha --version`, `artha init`,
`artha config show`, `artha secrets ...`). Screening, dossiers, the ledger,
monitoring, and execution are later phases — the corresponding CLI
subcommands (`screen`, `research`, `review`, `order`) are present as
documented stubs that refuse to run until their phase lands.

### Setup

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"

# Copy the config template and fill in your real values (this file is gitignored):
Copy-Item config\artha.example.toml config\artha.toml

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

### Credentials

Never put credentials in the repo or in env files. Store them in the OS
keyring:

```powershell
.venv\Scripts\artha secrets set kite_api_key
.venv\Scripts\artha secrets get kite_api_key   # reports set/not-set only
```
