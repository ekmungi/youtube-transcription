"""Application state management for the Flet UI. Immutable via frozen dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class VideoJob:
    """State for a single video being processed.

    Attributes:
        video_id: YouTube video ID.
        title: Video title for display.
        url: Full YouTube URL.
        status: One of "waiting", "running", "completed", "failed".
        progress: Progress percentage (0.0 to 1.0).
        file_path: Path to saved .md file (set on completion).
        error: Error message (set on failure).
    """
    video_id: str
    title: str
    url: str
    status: str = "waiting"
    progress: float = 0.0
    file_path: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class AppState:
    """Immutable application state. Create new instances via replace().

    Attributes:
        processing: Tuple of jobs currently being processed.
        completed: Tuple of finished jobs.
        is_transcribing: Whether a transcription batch is in progress.
    """
    processing: tuple[VideoJob, ...] = ()
    completed: tuple[VideoJob, ...] = ()
    is_transcribing: bool = False


def add_processing_job(state: AppState, job: VideoJob) -> AppState:
    """Add a new job to the processing queue. Returns new state.

    Args:
        state: Current application state.
        job: VideoJob to add.

    Returns:
        New AppState with the job appended to processing.
    """
    return replace(state, processing=(*state.processing, job))


def update_job_progress(state: AppState, video_id: str, progress: float) -> AppState:
    """Update progress for a processing job. Returns new state.

    Args:
        state: Current application state.
        video_id: ID of the job to update.
        progress: New progress value (0.0 to 1.0).

    Returns:
        New AppState with updated progress.
    """
    updated = tuple(
        replace(j, progress=progress, status="running") if j.video_id == video_id else j
        for j in state.processing
    )
    return replace(state, processing=updated)


def complete_job(state: AppState, video_id: str, file_path: str) -> AppState:
    """Move a job from processing to completed. Returns new state.

    Args:
        state: Current application state.
        video_id: ID of the job to complete.
        file_path: Path to the saved markdown file.

    Returns:
        New AppState with the job moved to completed.
    """
    job = next((j for j in state.processing if j.video_id == video_id), None)
    if job is None:
        return state

    remaining = tuple(j for j in state.processing if j.video_id != video_id)
    done_job = replace(job, status="completed", progress=1.0, file_path=file_path)
    return replace(
        state,
        processing=remaining,
        completed=(*state.completed, done_job),
    )


def fail_job(state: AppState, video_id: str, error: str) -> AppState:
    """Mark a processing job as failed. Returns new state.

    Args:
        state: Current application state.
        video_id: ID of the job to mark as failed.
        error: Error message to display.

    Returns:
        New AppState with the job marked as failed.
    """
    updated = tuple(
        replace(j, status="failed", error=error) if j.video_id == video_id else j
        for j in state.processing
    )
    return replace(state, processing=updated)
