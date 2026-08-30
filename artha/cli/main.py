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
from artha.engine.adapters import coverage_report, feature_vectors_from_rows
from artha.engine.ranking import rank as rank_universe
from artha.engine.spec import FormulaSpecError, load_formula_spec
from artha.journal import Journal
from artha.ledger.positions import list_open_positions
from artha.ledger.scorecard import (
    compare_to_benchmark,
    fund_annualized_return,
    get_benchmark_nav_series,
    record_benchmark_nav,
    track_scorecard,
)
from artha.ledger.tax_lots import SellDisciplineError, record_buy, record_sell
from artha.screening.loader import build_company_records
from artha.screening.pipeline import screen_track_a, screen_track_b
from artha.secrets import SecretNotFoundError, delete_secret, has_secret, set_secret

DEFAULT_CONFIG_PATH = "config/artha.toml"
DEFAULT_FORMULA_PATH = "config/formula.toml"
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


@cli.group()
def ledger() -> None:
    """Paper (or real) ledger: tax lots, positions, and the per-track scorecard (Phase 4)."""


@ledger.command("buy")
@click.argument("ticker")
@click.option("--track", type=click.Choice(["A", "B"]), required=True)
@click.option("--quantity", type=float, required=True)
@click.option("--price", type=float, required=True)
@click.option("--trade-date", required=True, help="ISO date, e.g. 2025-01-15.")
@click.option("--note", default=None)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def ledger_buy(ticker: str, track: str, quantity: float, price: float, trade_date: str, note: str | None, config_path: str) -> None:
    """Record a BUY: creates a new, fully-open tax lot."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        lot = record_buy(conn, ticker=ticker, track=track, quantity=quantity, price=price, trade_date=trade_date, note=note)
        Journal(conn).append(
            event_type="trade_buy",
            entity_type="tax_lot",
            entity_id=lot.lot_id,
            payload={"ticker": ticker, "track": track, "quantity": quantity, "price": price, "trade_date": trade_date, "note": note},
        )
    finally:
        conn.close()
    click.echo(f"lot_id: {lot.lot_id}  bought {quantity} {ticker} @ {price} on {trade_date}")


@ledger.command("sell")
@click.argument("ticker")
@click.option("--quantity", type=float, required=True)
@click.option("--price", type=float, required=True)
@click.option("--trade-date", required=True, help="ISO date, e.g. 2025-06-01.")
@click.option("--override-reason", default=None, help="Required if any consumed lot is held <12 months (config/ips.md §5).")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def ledger_sell(ticker: str, quantity: float, price: float, trade_date: str, override_reason: str | None, config_path: str) -> None:
    """Record a SELL: consumes open lots FIFO, producing one realized gain per lot touched."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        try:
            realized = record_sell(
                conn, ticker=ticker, quantity=quantity, price=price, trade_date=trade_date, override_reason=override_reason
            )
        except SellDisciplineError as exc:
            click.echo(str(exc), err=True)
            sys.exit(1)
        Journal(conn).append(
            event_type="trade_sell",
            entity_type="ticker",
            entity_id=ticker,
            payload={
                "ticker": ticker,
                "quantity": quantity,
                "price": price,
                "trade_date": trade_date,
                "override_reason": override_reason,
                "realized_gains": [
                    {"lot_id": rg.lot_id, "quantity": rg.quantity, "gain": rg.gain, "gain_type": rg.gain_type, "holding_days": rg.holding_days}
                    for rg in realized
                ],
            },
        )
    finally:
        conn.close()
    click.echo(f"sold {quantity} {ticker} @ {price} on {trade_date}")
    for rg in realized:
        click.echo(f"  realized {rg.gain_type}: qty={rg.quantity} gain={rg.gain:.2f} (holding_days={rg.holding_days})")


@ledger.command("positions")
@click.option("--track", type=click.Choice(["A", "B"]), default=None)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def ledger_positions(track: str | None, config_path: str) -> None:
    """List open positions, optionally filtered by track."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        positions = list_open_positions(conn, track=track)
    finally:
        conn.close()
    if not positions:
        click.echo("no open positions.")
        return
    for p in positions:
        click.echo(f"{p.ticker} (track {p.track}): qty={p.quantity}  avg_cost={p.avg_cost_per_unit:.2f}  cost_basis={p.cost_basis:.2f}")


@ledger.command("import-benchmark-nav")
@click.option("--fund-name", required=True, help="Must match config/artha.toml's [benchmark] fund name exactly.")
@click.option("--nav-date", required=True)
@click.option("--nav", type=float, required=True)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def ledger_import_benchmark_nav(fund_name: str, nav_date: str, nav: float, config_path: str) -> None:
    """Record one NAV point for a frozen-benchmark fund."""
    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        record_benchmark_nav(conn, fund_name=fund_name, nav_date=nav_date, nav=nav)
        Journal(conn).append(
            event_type="benchmark_nav_recorded",
            entity_type="benchmark_nav",
            entity_id=fund_name,
            payload={"fund_name": fund_name, "nav_date": nav_date, "nav": nav},
        )
    finally:
        conn.close()
    click.echo(f"recorded {fund_name} NAV {nav} on {nav_date}")


@ledger.command("scorecard")
@click.option("--track", type=click.Choice(["A", "B"]), required=True)
@click.option("--as-of-date", required=True)
@click.option("--price", "prices", multiple=True, help="TICKER=PRICE, repeatable — the current mark for each open position.")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def ledger_scorecard(track: str, as_of_date: str, prices: tuple[str, ...], config_path: str) -> None:
    """Compute the post-tax, money-weighted scorecard for one track (plan.md §9)."""
    current_prices: dict[str, float] = {}
    for entry in prices:
        if "=" not in entry:
            click.echo(f"invalid --price {entry!r}; expected TICKER=PRICE", err=True)
            sys.exit(1)
        ticker, _, value = entry.partition("=")
        try:
            current_prices[ticker] = float(value)
        except ValueError:
            click.echo(f"invalid price in --price {entry!r}", err=True)
            sys.exit(1)

    app_config = _load_config_or_default(config_path)
    conn = connect(app_config.db_path)
    try:
        apply_migrations(conn)
        card = track_scorecard(conn, track=track, as_of_date=as_of_date, current_prices=current_prices)

        index_series = get_benchmark_nav_series(conn, app_config.benchmark.index_fund_name)
        factor_series = get_benchmark_nav_series(conn, app_config.benchmark.factor_fund_name)
        comparison = None
        if len(index_series) >= 2 and len(factor_series) >= 2:
            index_return = fund_annualized_return(index_series)
            factor_return = fund_annualized_return(factor_series)
            comparison = compare_to_benchmark(card.xirr_post_tax, index_return, factor_return)

        Journal(conn).append(
            event_type="scorecard_computed",
            entity_type="track",
            entity_id=track,
            payload={
                "as_of_date": as_of_date,
                "invested_capital": card.invested_capital,
                "realized_tax": card.realized_tax,
                "accrued_tax_on_unrealized": card.accrued_tax_on_unrealized,
                "gross_ending_value": card.gross_ending_value,
                "post_tax_ending_value": card.post_tax_ending_value,
                "xirr_gross": card.xirr_gross,
                "xirr_post_tax": card.xirr_post_tax,
                "beats_benchmark_set": comparison.beats_benchmark_set if comparison else None,
            },
        )
    finally:
        conn.close()

    click.echo(f"track {track} scorecard as of {as_of_date}:")
    click.echo(f"  invested capital: {card.invested_capital:.2f}")
    click.echo(f"  realized tax: {card.realized_tax:.2f}")
    click.echo(f"  accrued tax on unrealized: {card.accrued_tax_on_unrealized:.2f}")
    click.echo(f"  gross ending value: {card.gross_ending_value:.2f}")
    click.echo(f"  post-tax ending value: {card.post_tax_ending_value:.2f}")
    click.echo(f"  XIRR (gross): {card.xirr_gross:.2%}")
    click.echo(f"  XIRR (post-tax): {card.xirr_post_tax:.2%}")
    if comparison:
        click.echo(f"  vs index fund ({app_config.benchmark.index_fund_name}): {comparison.index_return:.2%} ({'beats' if comparison.beats_index else 'trails'})")
        click.echo(f"  vs factor fund ({app_config.benchmark.factor_fund_name}): {comparison.factor_return:.2%} ({'beats' if comparison.beats_factor else 'trails'})")
        click.echo(f"  beats frozen benchmark set: {comparison.beats_benchmark_set}")
    else:
        click.echo("  (no benchmark NAV history yet — run 'artha ledger import-benchmark-nav' for both funds, at least 2 points each)")


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
@click.option("--source", required=True, help="Snapshot source label, e.g. 'screener_profile1'.")
@click.option("--profile", default="profile_1_standard", show_default=True)
@click.option("--track", type=click.Choice(["A", "B"]), required=True)
@click.option("--formula", "formula_path", default=DEFAULT_FORMULA_PATH, show_default=True)
@click.option("--top", default=25, show_default=True, help="How many ranked names to print.")
@click.option("--explain", is_flag=True, help="Show feature coverage across the universe.")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def rank(
    source: str,
    profile: str,
    track: str,
    formula_path: str,
    top: int,
    explain: bool,
    config_path: str,
) -> None:
    """Rank a snapshot by expected post-tax return (engine rebuild).

    Runs alongside `artha screen`. Candidates land in exactly one of three
    buckets: ranked, rejected by a named hard gate, or blocked by missing
    data — so a zero-length shortlist always says which of the two it was.
    """
    app_config = _load_config_or_default(config_path)

    try:
        spec = load_formula_spec(formula_path)
    except FormulaSpecError as exc:
        click.echo(f"formula spec error: {exc}", err=True)
        sys.exit(1)

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
        universe = feature_vectors_from_rows(
            rows, field_map, profile=profile, as_of=record.captured_at
        )
        run = rank_universe(universe, spec, track=track)

        Journal(conn).append(
            event_type="rank_run",
            entity_type="snapshot",
            entity_id=record.snapshot_id,
            payload={
                "track": track,
                "source": source,
                "profile": profile,
                "spec_version": run.spec_version,
                "spec_fingerprint": run.spec_fingerprint,
                "universe_size": len(universe),
                "ranked": [
                    {
                        "ticker": c.ticker,
                        "net_cagr": c.net_cagr,
                        "confidence": c.estimate.confidence,
                        "pending_verification": list(c.pending_verification),
                    }
                    for c in run.ranked[:top]
                ],
                "rejected_count": len(run.rejected),
                "insufficient_count": len(run.insufficient),
            },
        )
    finally:
        conn.close()

    click.echo(
        f"universe: {len(universe)}  ranked: {len(run.ranked)}  "
        f"rejected: {len(run.rejected)}  insufficient data: {len(run.insufficient)}"
    )
    click.echo(f"formula: {run.spec_version} ({run.spec_fingerprint})  snapshot: {record.snapshot_id[:12]}")

    if run.ranked:
        click.echo(
            f"\ntop {min(top, len(run.ranked))} by expected post-tax CAGR weighted by evidence confidence:"
        )
        for position, c in enumerate(run.ranked[:top], start=1):
            flag = " *" if c.pending_verification else ""
            click.echo(
                f"  {position:>3}. {c.ticker:<28} net {c.net_cagr:>7.1%}  "
                f"gross {c.estimate.gross_cagr:>7.1%}  confidence {c.estimate.confidence:>5.0%}{flag}"
            )
        awaiting = sum(1 for c in run.ranked if c.pending_verification)
        if awaiting:
            click.echo(
                f"\n  * {awaiting} of {len(run.ranked)} ranked names carry an unresolved Stage 1b check "
                "and are not buyable until it is answered."
            )
    else:
        click.echo("\nnothing ranked. the counts above say whether that is rejection or missing data.")

    if run.rejected:
        click.echo("\nrejections by rule:")
        for rule, count in _tally(r.reasons[0].split(":")[0] for r in run.rejected if r.reasons):
            click.echo(f"  {rule}: {count}")

    if run.insufficient:
        click.echo("\nblocked by missing data:")
        for reason, count in _tally(r for c in run.insufficient for r in c.reasons):
            click.echo(f"  {reason}: {count}")

    if explain:
        click.echo("\nfeature coverage across the universe:")
        for feature, share in coverage_report(universe).items():
            click.echo(f"  {feature:<40} {share:>6.1%}")


def _tally(items) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])


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
