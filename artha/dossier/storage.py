"""Dossier storage: the immutable markdown file + the queryable SQLite
index row (implementation_plan.md §16 Q1's "both" resolution).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from artha.dossier.render import render_markdown
from artha.dossier.schema import Dossier
from artha.dossier.validator import ValidationResult, validate_dossier


class DossierAlreadyExistsError(Exception):
    """Raised when writing to a (ticker, run_id) path that already exists.

    Dossiers are immutable once written — a revision must use a new
    run_id, never overwrite a prior file. This preserves plan.md §6's
    "immutable once approved, versioned in git" even for pre-approval
    drafts, so the git history is never silently rewritten underneath a
    run_id someone may already be reviewing.
    """


@dataclass(frozen=True)
class DossierWriteResult:
    run_id: str
    file_path: str
    validation: ValidationResult


def _safe_dir_name(name: str) -> str:
    """Sanitize a ticker for use as a directory-name path component.

    Windows silently strips trailing dots and spaces from directory names
    (a Win32 CreateDirectory quirk) — e.g. mkdir("Eco Recyc.") actually
    creates "Eco Recyc" on disk with no error and no visible sign anything
    happened. Screener.in tickers routinely end in "." (abbreviated
    company names), so left unsanitized this silently produces a directory
    whose name doesn't match `dossier.identity.ticker`, and — worse —
    would produce a *different* directory tree on Windows than on Linux/Mac
    (where the trailing dot is preserved), an even harder bug to notice.
    Stripped here explicitly and consistently across platforms so the
    behavior is deterministic and identical everywhere, matching what
    Windows already does silently.
    """
    return name.rstrip(". ") or name


def write_dossier_file(dossier: Dossier, *, run_id: str, dossiers_root: str | Path = "dossiers") -> Path:
    """Write the immutable markdown artifact to dossiers/<ticker>/<run_id>.md."""
    root = Path(dossiers_root)
    ticker_dir = root / _safe_dir_name(dossier.identity.ticker)
    ticker_dir.mkdir(parents=True, exist_ok=True)
    file_path = ticker_dir / f"{run_id}.md"
    if file_path.exists():
        raise DossierAlreadyExistsError(f"{file_path} already exists — dossiers are immutable; use a new run_id")
    file_path.write_text(render_markdown(dossier), encoding="utf-8")
    return file_path


def _extract_scores(dossier: Dossier) -> dict:
    return {
        "qglp_combined_score": dossier.qglp_scorecard.combined_score,
    }


def _extract_gates(dossier: Dossier) -> dict:
    return {
        "moat_understandability_gate_passed": dossier.moat_understandability_gate.passed,
        "integrity_gate_passed": dossier.integrity_gate.passed,
    }


def insert_dossier_index(
    conn: sqlite3.Connection,
    dossier: Dossier,
    *,
    run_id: str,
    file_path: str,
    stage: str,
    validation: ValidationResult,
    factory_run_id: str | None = None,
    agent_skill_commit_sha: str | None = None,
    model: str | None = None,
) -> None:
    """Insert the queryable index row for a written dossier."""
    created_at = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO dossiers
                (run_id, ticker, track, arithmetic_profile, snapshot_id, stage, file_path,
                 factory_run_id, agent_skill_commit_sha, model, validation_passed,
                 validation_errors_json, scores_json, gates_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                dossier.identity.ticker,
                dossier.identity.track,
                dossier.identity.arithmetic_profile,
                dossier.identity.snapshot_id,
                stage,
                file_path,
                factory_run_id,
                agent_skill_commit_sha,
                model,
                1 if validation.passed else 0,
                json.dumps([{"section": e.section, "reason": e.reason} for e in validation.errors]),
                json.dumps(_extract_scores(dossier)),
                json.dumps(_extract_gates(dossier)),
                created_at,
            ),
        )


def write_dossier(
    conn: sqlite3.Connection,
    dossier: Dossier,
    *,
    run_id: str,
    dossiers_root: str | Path = "dossiers",
    stage: str = "draft",
    factory_run_id: str | None = None,
    agent_skill_commit_sha: str | None = None,
    model: str | None = None,
) -> DossierWriteResult:
    """Validate, write the markdown file, and index it — the one entry
    point Phase 3a's factory (and any manual/CLI path) should call.

    Writes the file even if validation fails — an invalid dossier is still
    recorded (with its errors), matching plan.md's "rejected by the
    tooling" framing: the tooling's job is to make the defect visible and
    blocking for approval, not to make the attempt disappear.
    """
    validation = validate_dossier(dossier)
    file_path = write_dossier_file(dossier, run_id=run_id, dossiers_root=dossiers_root)
    insert_dossier_index(
        conn,
        dossier,
        run_id=run_id,
        file_path=str(file_path),
        stage=stage if validation.passed else "rejected",
        validation=validation,
        factory_run_id=factory_run_id,
        agent_skill_commit_sha=agent_skill_commit_sha,
        model=model,
    )
    return DossierWriteResult(run_id=run_id, file_path=str(file_path), validation=validation)
