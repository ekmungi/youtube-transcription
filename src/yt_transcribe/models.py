"""Immutable data models for the yt-transcribe system."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TranscriptionStrategy(StrEnum):
    """Available transcription strategy options."""
    AUTO = "auto"
    CAPTIONS = "captions"
    CLOUD = "cloud"
    LOCAL = "local"


class WhisperModel(StrEnum):
    """Available Whisper model sizes."""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"


class JobStatus(StrEnum):
    """Job lifecycle states."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class Config:
    """Application configuration. Loaded from ~/.yt-transcribe/config.yaml."""
    obsidian_vault_path: str
    transcript_folder: str
    transcription_strategy: TranscriptionStrategy
    whisper_model: WhisperModel
    async_threshold_seconds: int
    parallel_enabled: bool
    ffmpeg_location: str = ""


@dataclass(frozen=True)
class VideoInfo:
    """Metadata about a single YouTube video."""
    video_id: str
    title: str
    channel: str
    url: str
    duration_seconds: int
    playlist_title: str | None


@dataclass(frozen=True)
class Segment:
    """A single timed transcript segment."""
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class Transcript:
    """Complete transcript for a video."""
    video: VideoInfo
    text: str
    segments: tuple[Segment, ...]


@dataclass(frozen=True)
class Job:
    """Async transcription job state."""
    job_id: str
    status: JobStatus
    videos: tuple[VideoInfo, ...]
    completed_count: int
    error: str | None
