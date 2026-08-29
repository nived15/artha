"""Citation-preserving filing chunker (implementation_plan.md §2: `data/filings.py`).

Every dossier claim must cite an exact (doc_id, page) — plan.md §6. This
module splits filing text into paragraph-aware chunks per page and stores
them keyed by (doc_id, page, chunk_index), so a later citation lookup
(the future agent harness's `get_filing_chunk(doc_id, page)` tool, per
implementation_plan.md §4) can retrieve exactly the text a claim points to.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

DEFAULT_MAX_CHUNK_CHARS = 2000


@dataclass(frozen=True)
class FilingRecord:
    doc_id: str
    source_path: str
    ticker: str | None
    doc_type: str | None
    captured_at: str
    ingested_at: str
    sha256: str


@dataclass(frozen=True)
class ChunkRecord:
    doc_id: str
    page: int
    chunk_index: int
    text: str
    sha256: str


def chunk_text(text: str, max_chars: int = DEFAULT_MAX_CHUNK_CHARS) -> list[str]:
    """Split text into chunks on paragraph boundaries, each <= max_chars.

    Paragraph-aware (splits on blank lines) rather than a fixed character
    window, so a citation's chunk boundary lands on a natural break and
    doesn't sever a sentence a claim is quoting.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = para
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def ingest_filing(
    conn: sqlite3.Connection,
    *,
    doc_id: str,
    source_path: str,
    pages: list[str],
    ticker: str | None = None,
    doc_type: str | None = None,
    captured_at: str | None = None,
    max_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> FilingRecord:
    """Ingest a filing as a list of per-page text (1 entry = 1 page, 1-indexed).

    Idempotent on doc_id: re-ingesting the same doc_id replaces its chunks
    (a filing is identified by doc_id, not content-hash, since the same
    logical filing may be re-supplied from a cleaner text extraction).
    """
    full_text = "\n\n".join(pages)
    doc_sha256 = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    captured_at = captured_at or date.today().isoformat()
    ingested_at = datetime.now(timezone.utc).isoformat()

    with conn:
        conn.execute(
            """
            INSERT INTO filings (doc_id, source_path, ticker, doc_type, captured_at, ingested_at, sha256)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                source_path = excluded.source_path,
                ticker = excluded.ticker,
                doc_type = excluded.doc_type,
                captured_at = excluded.captured_at,
                ingested_at = excluded.ingested_at,
                sha256 = excluded.sha256
            """,
            (doc_id, source_path, ticker, doc_type, captured_at, ingested_at, doc_sha256),
        )
        conn.execute("DELETE FROM filing_chunks WHERE doc_id = ?", (doc_id,))
        for page_num, page_text in enumerate(pages, start=1):
            for chunk_index, chunk in enumerate(chunk_text(page_text, max_chars)):
                chunk_sha256 = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
                conn.execute(
                    """
                    INSERT INTO filing_chunks (doc_id, page, chunk_index, text, sha256)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (doc_id, page_num, chunk_index, chunk, chunk_sha256),
                )

    return FilingRecord(
        doc_id=doc_id,
        source_path=source_path,
        ticker=ticker,
        doc_type=doc_type,
        captured_at=captured_at,
        ingested_at=ingested_at,
        sha256=doc_sha256,
    )


def ingest_filing_from_file(
    conn: sqlite3.Connection,
    *,
    doc_id: str,
    path: str | Path,
    ticker: str | None = None,
    doc_type: str | None = None,
    captured_at: str | None = None,
    max_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> FilingRecord:
    """Ingest a plain-text filing file as a single page (page=1).

    For filings that already come as separate per-page text, call
    ingest_filing() directly with the `pages` list instead.
    """
    text = Path(path).read_text(encoding="utf-8")
    return ingest_filing(
        conn,
        doc_id=doc_id,
        source_path=str(path),
        pages=[text],
        ticker=ticker,
        doc_type=doc_type,
        captured_at=captured_at,
        max_chars=max_chars,
    )


def get_chunk(conn: sqlite3.Connection, doc_id: str, page: int, chunk_index: int = 0) -> ChunkRecord | None:
    """Look up one exact (doc_id, page, chunk_index) — the citation contract."""
    row = conn.execute(
        "SELECT doc_id, page, chunk_index, text, sha256 FROM filing_chunks "
        "WHERE doc_id = ? AND page = ? AND chunk_index = ?",
        (doc_id, page, chunk_index),
    ).fetchone()
    return ChunkRecord(**dict(row)) if row else None


def list_chunks(conn: sqlite3.Connection, doc_id: str, page: int | None = None) -> list[ChunkRecord]:
    """List chunks for a filing, optionally restricted to one page."""
    if page is None:
        rows = conn.execute(
            "SELECT doc_id, page, chunk_index, text, sha256 FROM filing_chunks "
            "WHERE doc_id = ? ORDER BY page, chunk_index",
            (doc_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT doc_id, page, chunk_index, text, sha256 FROM filing_chunks "
            "WHERE doc_id = ? AND page = ? ORDER BY chunk_index",
            (doc_id, page),
        ).fetchall()
    return [ChunkRecord(**dict(row)) for row in rows]
