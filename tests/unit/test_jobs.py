"""Tests for SQLite job manager."""

import sqlite3
from pathlib import Path

import pytest

from yt_transcribe.jobs import (
    create_job,
    get_job,
    get_or_create_db,
    list_jobs,
    update_job_status,
)
from yt_transcribe.models import JobStatus, VideoInfo


def _make_video(video_id: str = "abc123") -> VideoInfo:
    """Build a VideoInfo with sensible defaults."""
    return VideoInfo(
        video_id=video_id,
        title="Test Video",
        channel="Test Channel",
        url=f"https://youtube.com/watch?v={video_id}",
        duration_seconds=600,
        playlist_title=None,
    )


class TestGetOrCreateDb:
    def test_creates_database_file(self, tmp_path: Path):
        db_path = tmp_path / "jobs.db"
        conn = get_or_create_db(db_path)
        conn.close()
        assert db_path.exists()

    def test_creates_jobs_table(self, tmp_path: Path):
        db_path = tmp_path / "jobs.db"
        conn = get_or_create_db(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_parent_directories(self, tmp_path: Path):
        db_path = tmp_path / "subdir" / "jobs.db"
        conn = get_or_create_db(db_path)
        conn.close()
        assert db_path.exists()

    def test_in_memory_database(self):
        conn = get_or_create_db(":memory:")
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
        )
        assert cursor.fetchone() is not None
        conn.close()


class TestCreateJob:
    def test_returns_job_id(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        job_id = create_job(conn, (video,))
        assert isinstance(job_id, str)
        assert len(job_id) > 0
        conn.close()

    def test_initial_status_is_queued(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        job_id = create_job(conn, (video,))
        job = get_job(conn, job_id)
        assert job is not None
        assert job["status"] == JobStatus.QUEUED
        conn.close()

    def test_stores_video_count(self):
        conn = get_or_create_db(":memory:")
        videos = (_make_video("v1"), _make_video("v2"), _make_video("v3"))
        job_id = create_job(conn, videos)
        job = get_job(conn, job_id)
        assert job is not None
        assert job["video_count"] == 3
        conn.close()

    def test_initial_completed_count_is_zero(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        job_id = create_job(conn, (video,))
        job = get_job(conn, job_id)
        assert job is not None
        assert job["completed_count"] == 0
        conn.close()

    def test_unique_job_ids(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        id1 = create_job(conn, (video,))
        id2 = create_job(conn, (video,))
        assert id1 != id2
        conn.close()


class TestUpdateJobStatus:
    def test_update_to_running(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        job_id = create_job(conn, (video,))
        update_job_status(conn, job_id, status=JobStatus.RUNNING)
        job = get_job(conn, job_id)
        assert job is not None
        assert job["status"] == JobStatus.RUNNING
        conn.close()

    def test_update_to_completed(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        job_id = create_job(conn, (video,))
        update_job_status(conn, job_id, status=JobStatus.COMPLETED, completed_count=1)
        job = get_job(conn, job_id)
        assert job is not None
        assert job["status"] == JobStatus.COMPLETED
        assert job["completed_count"] == 1
        conn.close()

    def test_update_to_failed_with_error(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        job_id = create_job(conn, (video,))
        update_job_status(conn, job_id, status=JobStatus.FAILED, error="Network timeout")
        job = get_job(conn, job_id)
        assert job is not None
        assert job["status"] == JobStatus.FAILED
        assert job["error"] == "Network timeout"
        conn.close()

    def test_increment_completed_count(self):
        conn = get_or_create_db(":memory:")
        videos = (_make_video("v1"), _make_video("v2"))
        job_id = create_job(conn, videos)
        update_job_status(conn, job_id, completed_count=1)
        update_job_status(conn, job_id, completed_count=2)
        job = get_job(conn, job_id)
        assert job is not None
        assert job["completed_count"] == 2
        conn.close()


class TestGetJob:
    def test_returns_none_for_unknown_id(self):
        conn = get_or_create_db(":memory:")
        assert get_job(conn, "nonexistent-id") is None
        conn.close()

    def test_returns_dict_with_expected_keys(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        job_id = create_job(conn, (video,))
        job = get_job(conn, job_id)
        assert job is not None
        expected_keys = {"job_id", "status", "video_count", "completed_count", "error", "created_at"}
        assert expected_keys.issubset(set(job.keys()))
        conn.close()

    def test_created_at_is_set(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        job_id = create_job(conn, (video,))
        job = get_job(conn, job_id)
        assert job is not None
        assert job["created_at"] is not None
        conn.close()


class TestListJobs:
    def test_empty_database(self):
        conn = get_or_create_db(":memory:")
        assert list_jobs(conn) == []
        conn.close()

    def test_lists_all_jobs(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        create_job(conn, (video,))
        create_job(conn, (video,))
        create_job(conn, (video,))
        jobs = list_jobs(conn)
        assert len(jobs) == 3
        conn.close()

    def test_most_recent_first(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        id1 = create_job(conn, (video,))
        id2 = create_job(conn, (video,))
        jobs = list_jobs(conn)
        assert jobs[0]["job_id"] == id2
        assert jobs[1]["job_id"] == id1
        conn.close()

    def test_limit_parameter(self):
        conn = get_or_create_db(":memory:")
        video = _make_video()
        for _ in range(5):
            create_job(conn, (video,))
        jobs = list_jobs(conn, limit=3)
        assert len(jobs) == 3
        conn.close()
