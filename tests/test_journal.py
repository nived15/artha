from __future__ import annotations

from artha.db import apply_migrations, connect
from artha.journal import GENESIS_HASH, Journal


def _journal(tmp_path) -> Journal:
    conn = connect(tmp_path / "artha.db")
    apply_migrations(conn)
    return Journal(conn)


def test_append_and_read_back(tmp_path):
    journal = _journal(tmp_path)

    entry = journal.append(
        event_type="decision",
        entity_type="candidate",
        entity_id="RELIANCE",
        payload={"outcome": "REJECTED", "reason": "fails ROCE screen"},
    )

    assert entry.prev_hash == GENESIS_HASH
    assert entry.row_hash

    entries = journal.all_entries()
    assert len(entries) == 1
    assert entries[0].payload == {"outcome": "REJECTED", "reason": "fails ROCE screen"}


def test_chain_links_sequential_entries(tmp_path):
    journal = _journal(tmp_path)

    first = journal.append("decision", "candidate", "A", {"n": 1})
    second = journal.append("decision", "candidate", "B", {"n": 2})

    assert second.prev_hash == first.row_hash
    assert first.row_hash != second.row_hash


def test_verify_chain_passes_for_untouched_journal(tmp_path):
    journal = _journal(tmp_path)
    for i in range(5):
        journal.append("decision", "candidate", f"T{i}", {"n": i})

    ok, reason = journal.verify_chain()
    assert ok is True
    assert reason is None


def test_verify_chain_detects_tampering(tmp_path):
    journal = _journal(tmp_path)
    journal.append("decision", "candidate", "A", {"n": 1})
    journal.append("decision", "candidate", "B", {"n": 2})

    # Simulate someone editing a row directly in the DB, bypassing append().
    journal._conn.execute(
        "UPDATE journal SET payload_json = ? WHERE entity_id = ?",
        ('{"n": 999}', "A"),
    )
    journal._conn.commit()

    ok, reason = journal.verify_chain()
    assert ok is False
    assert "tampered" in reason


def test_verify_chain_detects_deleted_row(tmp_path):
    journal = _journal(tmp_path)
    journal.append("decision", "candidate", "A", {"n": 1})
    journal.append("decision", "candidate", "B", {"n": 2})
    journal.append("decision", "candidate", "C", {"n": 3})

    journal._conn.execute("DELETE FROM journal WHERE entity_id = ?", ("B",))
    journal._conn.commit()

    ok, reason = journal.verify_chain()
    assert ok is False
    assert "chain broken" in reason
