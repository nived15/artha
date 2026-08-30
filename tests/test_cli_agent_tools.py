from __future__ import annotations

import json

from click.testing import CliRunner

from artha.cli.main import cli

CONFIG_TOML = """
db_path = ".artha/artha.db"

[ips]
statement_path = "config/ips.md"

[benchmark]
index_fund_name = "UTI Nifty 50 Index Fund"
index_fund_isin = "INF789F01XA1"
factor_fund_name = "Nifty Quality 30 Index Fund"
factor_fund_isin = "INF789F01XA2"

[data]
field_map_path = "screener_field_map.toml"
snapshot_max_age_days = 100000
"""

FIELD_MAP_TOML = """
[profile_1_standard]
market_cap = "Market Capitalization"
roce = "ROCE"
"""

CSV_HEADER = "Name,Market Capitalization,ROCE"
CSV_ROW = "Alpha Ltd,1000,22"


def _setup(tmp_path):
    (tmp_path / "screener_field_map.toml").write_text(FIELD_MAP_TOML, encoding="utf-8")
    config_path = tmp_path / "artha.toml"
    config_path.write_text(CONFIG_TOML, encoding="utf-8")
    csv_path = tmp_path / "export.csv"
    csv_path.write_text(CSV_HEADER + "\r\n" + CSV_ROW + "\r\n", encoding="utf-8")
    return config_path, csv_path


def test_get_candidate_returns_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, csv_path = _setup(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["data", "import-screener", str(csv_path), "--source", "s1", "--config", str(config_path)])

    result = runner.invoke(cli, ["agent-tools", "get-candidate", "Alpha Ltd", "--source", "s1", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ticker"] == "Alpha Ltd"
    assert payload["fields"]["market_cap"] == 1000.0


def test_get_candidate_not_found_reports_error_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, csv_path = _setup(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["data", "import-screener", str(csv_path), "--source", "s1", "--config", str(config_path)])

    result = runner.invoke(cli, ["agent-tools", "get-candidate", "Nonexistent", "--source", "s1", "--config", str(config_path)])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "error" in payload


def test_get_candidate_requires_source_or_snapshot_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, _ = _setup(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["agent-tools", "get-candidate", "Alpha Ltd", "--config", str(config_path)])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "error" in payload


def test_get_filing_chunk_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, _ = _setup(tmp_path)
    filing_path = tmp_path / "filing.txt"
    filing_path.write_text("Quarterly commentary text.", encoding="utf-8")
    runner = CliRunner()
    runner.invoke(cli, ["data", "import-filing", str(filing_path), "--doc-id", "DOC1", "--ticker", "Alpha Ltd", "--config", str(config_path)])

    result = runner.invoke(cli, ["agent-tools", "get-filing-chunk", "DOC1", "1", "--config", str(config_path)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "Quarterly commentary text." in payload["text"]


def test_list_candidate_chunks_filters_by_topic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, _ = _setup(tmp_path)
    filing_path = tmp_path / "filing.txt"
    filing_path.write_text("Margins improved.\n\nPromoter pledge is zero.", encoding="utf-8")
    runner = CliRunner()
    runner.invoke(cli, ["data", "import-filing", str(filing_path), "--doc-id", "DOC1", "--ticker", "Alpha Ltd", "--config", str(config_path)])

    result = runner.invoke(cli, ["agent-tools", "list-candidate-chunks", "Alpha Ltd", "--topic", "pledge", "--config", str(config_path)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload["chunks"]) == 1
    assert "pledge" in payload["chunks"][0]["text"].lower()


def test_validate_dossier_tool_rejects_invalid_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["agent-tools", "validate-dossier"], input="not json")
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["passed"] is False


def test_write_dossier_tool_writes_and_indexes(tmp_path, monkeypatch):
    from tests.conftest import dossier_to_dict, make_valid_dossier

    monkeypatch.chdir(tmp_path)
    config_path, csv_path = _setup(tmp_path)
    runner = CliRunner()
    # Ingest a snapshot so the FK-referenced snapshot_id exists.
    import_result = runner.invoke(cli, ["data", "import-screener", str(csv_path), "--source", "s1", "--config", str(config_path)])
    snapshot_id = [line for line in import_result.output.splitlines() if line.startswith("snapshot_id:")][0].split(": ")[1]

    dossier = make_valid_dossier("A")
    import dataclasses

    dossier = dataclasses.replace(dossier, identity=dataclasses.replace(dossier.identity, snapshot_id=snapshot_id))
    draft_json = json.dumps(dossier_to_dict(dossier))

    result = runner.invoke(
        cli,
        ["agent-tools", "write-dossier", "--run-id", "run-1", "--config", str(config_path)],
        input=draft_json,
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["validation_passed"] is True
    assert (tmp_path / "dossiers" / "ALPHA" / "run-1.md").is_file()


def test_write_dossier_tool_preserves_non_ascii_stdin(tmp_path, monkeypatch):
    """Regression test: piped stdin must be decoded as UTF-8, not the
    platform default (cp1252 on Windows), or non-ASCII characters like
    "§" get corrupted into mojibake before json.loads ever sees them."""
    from tests.conftest import dossier_to_dict, make_valid_dossier
    import dataclasses

    monkeypatch.chdir(tmp_path)
    config_path, csv_path = _setup(tmp_path)
    runner = CliRunner()
    import_result = runner.invoke(cli, ["data", "import-screener", str(csv_path), "--source", "s1", "--config", str(config_path)])
    snapshot_id = [line for line in import_result.output.splitlines() if line.startswith("snapshot_id:")][0].split(": ")[1]

    dossier = make_valid_dossier("A")
    dossier = dataclasses.replace(dossier, identity=dataclasses.replace(dossier.identity, snapshot_id=snapshot_id))
    draft = dossier_to_dict(dossier)
    non_ascii = "See plan.md §6 for the citation rule; ₹1.25 lakh exemption; an em dash — here."
    draft["why_now"]["content"] = non_ascii
    draft_json_bytes = json.dumps(draft).encode("utf-8")

    result = runner.invoke(
        cli,
        ["agent-tools", "write-dossier", "--run-id", "run-2", "--config", str(config_path)],
        input=draft_json_bytes,
    )
    assert result.exit_code == 0, result.output
    written = (tmp_path / "dossiers" / "ALPHA" / "run-2.md").read_text(encoding="utf-8")
    assert non_ascii in written
