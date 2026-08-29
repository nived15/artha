"""Artha CLI.

plan.md §11 Phase 0 exit criterion: `artha --version` runs. The other
subcommands are stubs for later phases (module layout in
implementation_plan.md §2: `cli/ # artha screen | artha research <ticker>
| artha review | artha order`) — they exist so the intended surface is
documented, but they refuse to run until their phase lands.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from artha import __version__
from artha.config import AppConfig, BenchmarkConfig, ConfigError, IPSConfig, load_config
from artha.data.field_map import load_field_map
from artha.data.filings import get_chunk, ingest_filing_from_file, list_chunks
from artha.data.screener_import import ingest_and_validate
from artha.data.snapshot import StaleSnapshotError, assert_not_stale, get_snapshot, latest_snapshot, load_rows
from artha.db import apply_migrations, connect, current_schema_version
from artha.dossier.serialization import DossierSchemaError, dossier_from_dict
from artha.dossier.storage import write_dossier
from artha.dossier.validator import validate_dossier
from artha.journal import Journal
from artha.screening.loader import build_company_records
from artha.screening.pipeline import screen_track_a, screen_track_b
from artha.secrets import SecretNotFoundError, delete_secret, has_secret, set_secret

DEFAULT_CONFIG_PATH = "config/artha.toml"
DEFAULT_DRY_RUN_SETTING = "dry_run_mode"


@click.group()
@click.version_option(version=__version__, prog_name="artha")
def cli() -> None:
    """Artha — a disciplined, documented Indian-equity research and execution pipeline."""


@cli.command()
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def init(config_path: str) -> None:
    """Bootstrap the local SQLite database and apply schema migrations.

    Reads db_path from config; falls back to the AppConfig default if the
    config file does not exist yet, so `artha init` also works before you've
    copied config/artha.example.toml to config/artha.toml.
    """
    try:
        config = load_config(config_path)
        db_path = config.db_path
    except ConfigError as exc:
        click.echo(f"warning: {exc}\n(using default db_path — copy config/artha.example.toml to {config_path} first)", err=True)
        db_path = ".artha/artha.db"

    conn = connect(db_path)
    try:
        applied = apply_migrations(conn)
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (DEFAULT_DRY_RUN_SETTING, "true"),
        )
        conn.commit()
        version = current_schema_version(conn)
    finally:
        conn.close()

    if applied:
        click.echo(f"applied migrations: {applied}")
    click.echo(f"database ready at {db_path} (schema version {version})")


@cli.group()
def config() -> None:
    """Inspect the resolved application config."""


@config.command("show")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def config_show(config_path: str) -> None:
    try:
        app_config = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"config error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"db_path: {app_config.db_path}")
    click.echo(f"ips.statement_path: {app_config.ips.statement_path}")
    click.echo(f"ips.frozen_on: {app_config.ips.frozen_on or '(not frozen)'}")
    click.echo(f"benchmark.index_fund_name: {app_config.benchmark.index_fund_name}")
    click.echo(f"benchmark.factor_fund_name: {app_config.benchmark.factor_fund_name}")
    click.echo(f"benchmark.frozen_on: {app_config.benchmark.frozen_on or '(not frozen)'}")
    click.echo(f"sizing: {app_config.sizing}")
    click.echo(f"budget: {app_config.budget}")


@cli.group()
def secrets() -> None:
    """Manage credentials in the OS keyring (plan.md §7.4). Never stored in the repo."""


@secrets.command("set")
@click.argument("name")
def secrets_set(name: str) -> None:
    value = click.prompt(f"value for '{name}'", hide_input=True)
    set_secret(name, value)
    click.echo(f"stored secret '{name}' in the OS keyring.")


@secrets.command("get")
@click.argument("name")
def secrets_get(name: str) -> None:
    """Report whether a secret is set, without printing its value."""
    if has_secret(name):
        click.echo(f"'{name}' is set.")
    else:
        click.echo(f"'{name}' is not set.", err=True)
        sys.exit(1)


@secrets.command("delete")
@click.argument("name")
def secrets_delete(name: str) -> None:
    try:
        delete_secret(name)
    except SecretNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(f"deleted secret '{name}'.")


def _not_implemented(phase: str) -> None:
    click.echo(
        f"not implemented yet — this command belongs to {phase}, which has not been built.\n"
        "See implementation_plan.md's build sequence.",
        err=True,
    )
    sys.exit(1)


@cli.group()
def data() -> None:
    """Data spine: ingest Screener exports and BSE filings (Phase 1)."""


@data.command("import-screener")
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--source", required=True, help="Source label, e.g. 'screener_profile1'.")
@click.option("--profile", default="profile_1_standard", show_default=True, help="§5.3a arithmetic profile name.")
@click.option("--captured-on", default=None, help="ISO date the export was taken (default: today).")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def data_import_screener(csv_path: str, source: str, profile: str, captured_on: str | None, config_path: str) -> None:
    """Ingest a Screener.in CSV export and run the §13.4 validation-spike checks."""
    app_config = _load_config_or_default(config_path)

    field_map = load_field_map(app_config.data.field_map_path, profile)
    csv_bytes = Path(csv_path).read_bytes()

    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        record, report = ingest_and_validate(
            conn,
            csv_bytes=csv_bytes,
            source=source,
            profile=profile,
            field_map=field_map,
            snapshot_dir=app_config.data.snapshot_dir,
            max_columns=app_config.data.max_export_columns,
            captured_at=captured_on,
        )
        Journal(conn).append(
            event_type="screener_export_ingested",
            entity_type="snapshot",
            entity_id=record.snapshot_id,
            payload={
                "source": source,
                "profile": profile,
                "row_count": report.row_count,
                "column_count": report.column_count,
                "column_ceiling_ok": report.column_ceiling_ok,
                "unmapped_fields": list(report.unmapped_fields),
                "missing_columns": list(report.missing_columns),
                "passed": report.passed,
            },
        )
    finally:
        conn.close()

    click.echo(f"snapshot_id: {record.snapshot_id}")
    click.echo(f"captured_at: {record.captured_at}")
    click.echo(f"rows: {report.row_count}  columns: {report.column_count} (ceiling: {report.max_columns})")
    click.echo(f"column_ceiling_ok: {report.column_ceiling_ok}")
    if report.unmapped_fields:
        click.echo(f"unmapped required fields (add to {app_config.data.field_map_path}): {list(report.unmapped_fields)}")
    if report.missing_columns:
        click.echo(f"required fields mapped but missing from CSV: {list(report.missing_columns)}")
    for fc in report.field_completeness:
        click.echo(f"  {fc.canonical_name}: {fc.completeness_pct:.1f}% ({fc.non_null_count}/{fc.total_count})")

    if not report.passed:
        click.echo("§13.4 validation spike: FAILED — see missing/unmapped fields above.", err=True)
        sys.exit(1)
    click.echo("§13.4 validation spike: passed (column ceiling + required-field checks).")


@data.command("show-snapshot")
@click.argument("snapshot_id")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def data_show_snapshot(snapshot_id: str, config_path: str) -> None:
    """Print stored metadata and field completeness for a snapshot."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        record = get_snapshot(conn, snapshot_id)
        if record is None:
            click.echo(f"no such snapshot: {snapshot_id}", err=True)
            sys.exit(1)
        rows = conn.execute(
            "SELECT field_name, completeness_pct FROM snapshot_fields WHERE snapshot_id = ? ORDER BY field_name",
            (snapshot_id,),
        ).fetchall()
    finally:
        conn.close()

    click.echo(f"snapshot_id: {record.snapshot_id}")
    click.echo(f"source: {record.source}  profile: {record.profile}")
    click.echo(f"captured_at: {record.captured_at}  ingested_at: {record.ingested_at}")
    click.echo(f"rows: {record.row_count}  columns: {record.column_count}")
    for row in rows:
        click.echo(f"  {row['field_name']}: {row['completeness_pct']:.1f}%")


@data.command("check-staleness")
@click.argument("snapshot_id")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def data_check_staleness(snapshot_id: str, config_path: str) -> None:
    """Apply the §13.6 staleness guard to a stored snapshot."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        record = get_snapshot(conn, snapshot_id)
        if record is None:
            click.echo(f"no such snapshot: {snapshot_id}", err=True)
            sys.exit(1)
    finally:
        conn.close()

    try:
        assert_not_stale(record, app_config.data.snapshot_max_age_days)
    except StaleSnapshotError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(f"snapshot {snapshot_id} is fresh (captured {record.captured_at}).")


@data.command("import-filing")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--doc-id", required=True)
@click.option("--ticker", default=None)
@click.option("--doc-type", default=None)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def data_import_filing(path: str, doc_id: str, ticker: str | None, doc_type: str | None, config_path: str) -> None:
    """Ingest a plain-text filing into the citation-preserving chunk store."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        record = ingest_filing_from_file(conn, doc_id=doc_id, path=path, ticker=ticker, doc_type=doc_type)
        Journal(conn).append(
            event_type="filing_ingested",
            entity_type="filing",
            entity_id=record.doc_id,
            payload={"source_path": record.source_path, "ticker": ticker, "doc_type": doc_type, "sha256": record.sha256},
        )
    finally:
        conn.close()
    click.echo(f"doc_id: {record.doc_id}  sha256: {record.sha256}")


@data.command("show-chunk")
@click.argument("doc_id")
@click.argument("page", type=int)
@click.option("--chunk-index", default=0, show_default=True)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def data_show_chunk(doc_id: str, page: int, chunk_index: int, config_path: str) -> None:
    """Print one stored (doc_id, page, chunk_index) chunk — the citation contract."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        chunk = get_chunk(conn, doc_id, page, chunk_index)
    finally:
        conn.close()
    if chunk is None:
        click.echo(f"no such chunk: ({doc_id}, page={page}, chunk_index={chunk_index})", err=True)
        sys.exit(1)
    click.echo(chunk.text)


def _load_config_or_default(config_path: str) -> AppConfig:
    try:
        return load_config(config_path)
    except ConfigError as exc:
        click.echo(f"warning: {exc}\n(using defaults — copy config/artha.example.toml to {config_path} first)", err=True)
        return AppConfig(ips=IPSConfig(statement_path=""), benchmark=BenchmarkConfig("", "", "", ""))


@cli.group("agent-tools")
def agent_tools() -> None:
    """Read-only JSON query surface for the Phase 3a agent harness.

    These commands are what .github/extensions/artha-tools/extension.mjs
    shells out to — the actual Copilot-facing tools (get_filing_chunk,
    get_candidate, list_candidate_chunks, validate_dossier) are thin
    JSON-in/JSON-out wrappers over these. Kept as plain CLI commands (not
    a long-running server) so the extension can invoke them per-call
    without managing any daemon lifecycle.
    """


@agent_tools.command("get-candidate")
@click.argument("ticker")
@click.option("--snapshot-id", default=None, help="Look up within this exact snapshot (matches implementation_plan.md §4's get_candidate(ticker, snapshot_id) tool signature).")
@click.option("--source", default=None, help="Alternative to --snapshot-id: resolve the latest snapshot for this source label.")
@click.option("--profile", default="profile_1_standard", show_default=True)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def agent_tools_get_candidate(ticker: str, snapshot_id: str | None, source: str | None, profile: str, config_path: str) -> None:
    """Print one candidate's resolved Stage 1a fields as JSON."""
    if not snapshot_id and not source:
        click.echo(json.dumps({"error": "one of --snapshot-id or --source is required"}))
        sys.exit(1)

    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        record = get_snapshot(conn, snapshot_id) if snapshot_id else latest_snapshot(conn, source)
        if record is None:
            click.echo(json.dumps({"error": f"no snapshot found for source={source!r} snapshot_id={snapshot_id!r}"}))
            sys.exit(1)
        rows = load_rows(record)
        field_map = load_field_map(app_config.data.field_map_path, profile)
        candidates = build_company_records(rows, field_map, arithmetic_profile=profile)
    finally:
        conn.close()

    match = next((c for c in candidates if c.ticker == ticker), None)
    if match is None:
        click.echo(json.dumps({"error": f"ticker {ticker!r} not found in snapshot {record.snapshot_id}"}))
        sys.exit(1)
    click.echo(json.dumps({"ticker": match.ticker, "arithmetic_profile": match.arithmetic_profile, "snapshot_id": record.snapshot_id, "fields": match.fields}))


@agent_tools.command("get-filing-chunk")
@click.argument("doc_id")
@click.argument("page", type=int)
@click.option("--chunk-index", default=0, show_default=True)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def agent_tools_get_filing_chunk(doc_id: str, page: int, chunk_index: int, config_path: str) -> None:
    """Print one (doc_id, page, chunk_index) citation chunk as JSON."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        chunk = get_chunk(conn, doc_id, page, chunk_index)
    finally:
        conn.close()
    if chunk is None:
        click.echo(json.dumps({"error": f"no such chunk: ({doc_id}, page={page}, chunk_index={chunk_index})"}))
        sys.exit(1)
    click.echo(json.dumps({"doc_id": chunk.doc_id, "page": chunk.page, "chunk_index": chunk.chunk_index, "text": chunk.text, "sha256": chunk.sha256}))


@agent_tools.command("list-candidate-chunks")
@click.argument("ticker")
@click.option("--topic", default=None, help="Case-insensitive substring filter over chunk text.")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def agent_tools_list_candidate_chunks(ticker: str, topic: str | None, config_path: str) -> None:
    """List citation chunks for every filing ingested under TICKER, as JSON."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        doc_ids = [row["doc_id"] for row in conn.execute("SELECT doc_id FROM filings WHERE ticker = ?", (ticker,)).fetchall()]
        chunks = []
        for doc_id in doc_ids:
            for chunk in list_chunks(conn, doc_id):
                if topic is None or topic.lower() in chunk.text.lower():
                    chunks.append({"doc_id": chunk.doc_id, "page": chunk.page, "chunk_index": chunk.chunk_index, "text": chunk.text})
    finally:
        conn.close()
    click.echo(json.dumps({"ticker": ticker, "chunks": chunks}))


@agent_tools.command("validate-dossier")
def agent_tools_validate_dossier() -> None:
    """Validate a dossier draft (JSON on stdin) without writing it. Prints JSON {passed, errors}."""
    try:
        draft = json.loads(sys.stdin.read())
        dossier = dossier_from_dict(draft)
    except (json.JSONDecodeError, DossierSchemaError) as exc:
        click.echo(json.dumps({"passed": False, "errors": [{"section": "draft", "reason": str(exc)}]}))
        sys.exit(1)

    result = validate_dossier(dossier)
    click.echo(json.dumps({"passed": result.passed, "errors": [{"section": e.section, "reason": e.reason} for e in result.errors]}))
    if not result.passed:
        sys.exit(1)


@agent_tools.command("write-dossier")
@click.option("--run-id", required=True)
@click.option("--dossiers-root", default="dossiers", show_default=True)
@click.option("--stage", default="draft", show_default=True)
@click.option("--factory-run-id", default=None)
@click.option("--agent-skill-commit-sha", default=None)
@click.option("--model", default=None)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def agent_tools_write_dossier(
    run_id: str,
    dossiers_root: str,
    stage: str,
    factory_run_id: str | None,
    agent_skill_commit_sha: str | None,
    model: str | None,
    config_path: str,
) -> None:
    """Validate, write, and index a dossier draft (JSON on stdin). Prints JSON result.

    This is the factory's own write step, not an agent-callable tool — the
    extension's read-only tool surface never exposes a write path.
    """
    try:
        draft = json.loads(sys.stdin.read())
        dossier = dossier_from_dict(draft)
    except (json.JSONDecodeError, DossierSchemaError) as exc:
        click.echo(json.dumps({"error": str(exc)}))
        sys.exit(1)

    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        result = write_dossier(
            conn,
            dossier,
            run_id=run_id,
            dossiers_root=dossiers_root,
            stage=stage,
            factory_run_id=factory_run_id,
            agent_skill_commit_sha=agent_skill_commit_sha,
            model=model,
        )
        Journal(conn).append(
            event_type="dossier_written",
            entity_type="dossier",
            entity_id=run_id,
            payload={
                "ticker": dossier.identity.ticker,
                "track": dossier.identity.track,
                "validation_passed": result.validation.passed,
                "errors": [{"section": e.section, "reason": e.reason} for e in result.validation.errors],
                "file_path": result.file_path,
            },
        )
    finally:
        conn.close()

    click.echo(
        json.dumps(
            {
                "run_id": result.run_id,
                "file_path": result.file_path,
                "validation_passed": result.validation.passed,
                "errors": [{"section": e.section, "reason": e.reason} for e in result.validation.errors],
            }
        )
    )
    if not result.validation.passed:
        sys.exit(1)


@cli.command()
@click.option("--source", required=True, help="Snapshot source label, e.g. 'screener_profile1' (matches import-screener).")
@click.option("--profile", default="profile_1_standard", show_default=True, help="§5.3a arithmetic profile name.")
@click.option("--track", type=click.Choice(["A", "B"]), required=True)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def screen(source: str, profile: str, track: str, config_path: str) -> None:
    """Run the Track A/B Stage 1+2 screening pipeline over the latest ingested snapshot."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        record = latest_snapshot(conn, source)
        if record is None:
            click.echo(f"no snapshot found for source={source}; run 'artha data import-screener' first.", err=True)
            sys.exit(1)
        try:
            assert_not_stale(record, app_config.data.snapshot_max_age_days)
        except StaleSnapshotError as exc:
            click.echo(str(exc), err=True)
            sys.exit(1)

        rows = load_rows(record)
        field_map = load_field_map(app_config.data.field_map_path, profile)
        company_records = build_company_records(rows, field_map, arithmetic_profile=profile)

        results = screen_track_a(company_records) if track == "A" else screen_track_b(company_records)
        shortlist = [c for c in results if not c.excluded and c.cleared_stage1]
        excluded = [c for c in results if c.excluded]
        pending = [c for c in results if not c.excluded and not c.cleared_stage1]

        Journal(conn).append(
            event_type="screen_run",
            entity_type="snapshot",
            entity_id=record.snapshot_id,
            payload={
                "track": track,
                "source": source,
                "profile": profile,
                "universe_size": len(company_records),
                "shortlist_size": len(shortlist),
                "shortlist": [c.ticker for c in shortlist],
                "exclusions": {c.ticker: list(c.exclusion_reasons) for c in excluded},
                "pending_insufficient_data": {c.ticker: list(c.insufficient_data_fields) for c in pending},
            },
        )
    finally:
        conn.close()

    click.echo(
        f"universe: {len(company_records)}  shortlist: {len(shortlist)}  "
        f"excluded: {len(excluded)}  pending (insufficient Stage 1a data): {len(pending)}"
    )
    click.echo("shortlist:")
    for c in shortlist:
        rank_note = f" (Greenblatt combined-rank percentile={c.greenblatt.percentile:.1f})" if c.greenblatt else ""
        click.echo(f"  {c.ticker}{rank_note}")
    if excluded:
        click.echo("excluded (rule attributed):")
        for c in excluded:
            click.echo(f"  {c.ticker}: {'; '.join(c.exclusion_reasons)}")
    if pending:
        click.echo("pending — insufficient Stage 1a data (not excluded, not shortlisted):")
        for c in pending:
            click.echo(f"  {c.ticker}: missing {list(c.insufficient_data_fields)}")


@cli.command()
@click.argument("ticker")
def research(ticker: str) -> None:
    """Run deep-dive research and generate a dossier for TICKER. (Phase 3 — not yet built.)"""
    _not_implemented("Phase 3 (deep research + dossiers)")


@cli.command()
def review() -> None:
    """Review pending dossiers and record Gate 1 (thesis approval) decisions. (Phase 3/4 — not yet built.)"""
    _not_implemented("Phase 3/4 (dossier review + paper ledger)")


@cli.command()
def order() -> None:
    """Confirm Gate 2 and place an order on Kite. (Phase 6 — not yet built.)"""
    _not_implemented("Phase 6 (execution)")


if __name__ == "__main__":
    cli()
