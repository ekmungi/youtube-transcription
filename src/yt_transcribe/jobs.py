"""SQLite-backed async job manager for background transcription processing."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from yt_transcribe.models import JobStatus, VideoInfo

# Default database location
JOBS_DB_PATH = Path.home() / ".yt-transcribe" / "jobs.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'queued',
    video_count INTEGER NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def get_or_create_db(path: Path | str = JOBS_DB_PATH) -> sqlite3.Connection:
    """Open or create the jobs SQLite database.

    Creates the jobs table if it does not exist. Supports both file paths
    and ':memory:' for testing.

    Args:
        path: Path to the SQLite database file, or ':memory:' for in-memory.

    Returns:
        Open SQLite connection with row_factory set to sqlite3.Row.
    """
    if isinstance(path, Path):
        path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    return conn


def create_job(conn: sqlite3.Connection, videos: tuple[VideoInfo, ...]) -> str:
    """Create a new job record in the database.

    Args:
        conn: Open database connection.
        videos: Tuple of videos to be processed by this job.

    Returns:
        Unique job ID string.
    """
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO jobs (job_id, status, video_count, completed_count, error, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (job_id, JobStatus.QUEUED, len(videos), 0, None, now, now),
    )
    conn.commit()
    return job_id


def update_job_status(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    status: JobStatus | None = None,
    completed_count: int | None = None,
    error: str | None = None,
) -> None:
    """Update one or more fields on an existing job.

    Only provided (non-None) fields are updated. Always bumps updated_at.

    Args:
        conn: Open database connection.
        job_id: ID of the job to update.
        status: New job status, or None to leave unchanged.
        completed_count: New completed video count, or None to leave unchanged.
        error: Error message, or None to leave unchanged.
    """
    updates: list[str] = []
    params: list[Any] = []

    if status is not None:
        updates.append("status = ?")
        params.append(str(status))
    if completed_count is not None:
        updates.append("completed_count = ?")
        params.append(completed_count)
    if error is not None:
        updates.append("error = ?")
        params.append(error)

    updates.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append(job_id)

    sql = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
    conn.execute(sql, params)
    conn.commit()


def get_job(conn: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
    """Fetch a single job by ID.

    Args:
        conn: Open database connection.
        job_id: ID of the job to fetch.

    Returns:
        Dict with job fields, or None if not found.
    """
    cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(row)


def list_jobs(
    conn: sqlite3.Connection,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List jobs ordered by most recently created first.

    Args:
        conn: Open database connection.
        limit: Maximum number of jobs to return (default 50).

    Returns:
        List of job dicts, newest first.
    """
    cursor = conn.execute(
        "SELECT * FROM jobs ORDER BY rowid DESC LIMIT ?",
        (limit,),
    )
    return [dict(row) for row in cursor.fetchall()]
