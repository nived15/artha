from __future__ import annotations

from artha.data.filings import chunk_text, get_chunk, ingest_filing, ingest_filing_from_file, list_chunks
from artha.db import apply_migrations, connect


def _fresh_conn(tmp_path):
    conn = connect(tmp_path / "artha.db")
    apply_migrations(conn)
    return conn


def test_chunk_text_splits_on_paragraph_boundaries_under_max_chars():
    text = "Para one.\n\nPara two.\n\nPara three is a bit longer than the others."
    chunks = chunk_text(text, max_chars=10)
    assert chunks == ["Para one.", "Para two.", "Para three is a bit longer than the others."]
    # Each individual paragraph is returned whole even if it exceeds max_chars alone,
    # but no chunk merges two paragraphs beyond the limit.
    assert "\n\n" not in chunks[0]


def test_chunk_text_merges_small_paragraphs_up_to_limit():
    text = "A.\n\nB.\n\nC."
    chunks = chunk_text(text, max_chars=100)
    assert chunks == ["A.\n\nB.\n\nC."]


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text("   \n\n  ") == []


def test_ingest_filing_stores_chunks_by_page(tmp_path):
    conn = _fresh_conn(tmp_path)
    record = ingest_filing(
        conn,
        doc_id="ANNUAL_REPORT_2024",
        source_path="filings/ar2024.txt",
        pages=["Page one text.", "Page two text.\n\nSecond paragraph on page two."],
        ticker="ALPHA",
        doc_type="annual_report",
        captured_at="2025-06-01",
    )

    assert record.doc_id == "ANNUAL_REPORT_2024"
    assert record.ticker == "ALPHA"

    page1_chunks = list_chunks(conn, "ANNUAL_REPORT_2024", page=1)
    assert len(page1_chunks) == 1
    assert page1_chunks[0].text == "Page one text."

    chunk = get_chunk(conn, "ANNUAL_REPORT_2024", page=2, chunk_index=0)
    assert chunk is not None
    assert "Page two text." in chunk.text


def test_get_chunk_returns_none_for_unknown_citation(tmp_path):
    conn = _fresh_conn(tmp_path)
    assert get_chunk(conn, "NOPE", page=1) is None


def test_ingest_filing_replaces_previous_chunks_on_re_ingest(tmp_path):
    conn = _fresh_conn(tmp_path)
    ingest_filing(conn, doc_id="D1", source_path="a.txt", pages=["Old text."])
    ingest_filing(conn, doc_id="D1", source_path="a.txt", pages=["New text.", "Second page."])

    chunks = list_chunks(conn, "D1")
    all_text = " ".join(c.text for c in chunks)
    assert "Old text." not in all_text
    assert "New text." in all_text


def test_ingest_filing_from_file_reads_single_page(tmp_path):
    conn = _fresh_conn(tmp_path)
    file_path = tmp_path / "filing.txt"
    file_path.write_text("Some filing content.\n\nAnother paragraph.", encoding="utf-8")

    record = ingest_filing_from_file(conn, doc_id="F1", path=file_path)
    assert record.doc_id == "F1"

    # Both short paragraphs fit under the default max_chars, so they merge
    # into a single chunk for page 1.
    chunks = list_chunks(conn, "F1", page=1)
    assert len(chunks) == 1
    assert "Some filing content." in chunks[0].text
    assert "Another paragraph." in chunks[0].text
