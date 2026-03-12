"""Tests for immutable data models."""

from yt_transcribe.models import (
    Config,
    Job,
    JobStatus,
    Segment,
    Transcript,
    TranscriptionStrategy,
    VideoInfo,
    WhisperModel,
)


class TestTranscriptionStrategy:
    def test_values(self):
        assert TranscriptionStrategy.AUTO == "auto"
        assert TranscriptionStrategy.CLOUD == "cloud"
        assert TranscriptionStrategy.LOCAL == "local"


class TestWhisperModel:
    def test_values(self):
        assert WhisperModel.TINY == "tiny"
        assert WhisperModel.BASE == "base"
        assert WhisperModel.SMALL == "small"
        assert WhisperModel.MEDIUM == "medium"


class TestJobStatus:
    def test_values(self):
        assert JobStatus.QUEUED == "queued"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"


class TestConfig:
    def test_creation(self):
        config = Config(
            obsidian_vault_path="/vault",
            transcript_folder="Transcripts",
            transcription_strategy=TranscriptionStrategy.AUTO,
            whisper_model=WhisperModel.BASE,
            async_threshold_seconds=180,
            parallel_enabled=False,
        )
        assert config.obsidian_vault_path == "/vault"
        assert config.transcription_strategy == TranscriptionStrategy.AUTO

    def test_frozen(self):
        config = Config(
            obsidian_vault_path="/vault",
            transcript_folder="Transcripts",
            transcription_strategy=TranscriptionStrategy.AUTO,
            whisper_model=WhisperModel.BASE,
            async_threshold_seconds=180,
            parallel_enabled=False,
        )
        import pytest
        with pytest.raises(AttributeError):
            config.obsidian_vault_path = "/other"  # type: ignore[misc]


class TestVideoInfo:
    def test_creation(self):
        video = VideoInfo(
            video_id="abc123",
            title="Test Video",
            channel="Test Channel",
            url="https://youtube.com/watch?v=abc123",
            duration_seconds=600,
            playlist_title=None,
        )
        assert video.video_id == "abc123"
        assert video.playlist_title is None

    def test_with_playlist(self):
        video = VideoInfo(
            video_id="abc123",
            title="Lecture 1",
            channel="MIT",
            url="https://youtube.com/watch?v=abc123",
            duration_seconds=3600,
            playlist_title="MIT 6.034",
        )
        assert video.playlist_title == "MIT 6.034"


class TestSegment:
    def test_creation(self):
        seg = Segment(start_seconds=0.0, end_seconds=5.5, text="Hello world")
        assert seg.start_seconds == 0.0
        assert seg.text == "Hello world"


class TestTranscript:
    def test_creation(self):
        video = VideoInfo(
            video_id="abc", title="T", channel="C",
            url="http://y.com", duration_seconds=60, playlist_title=None,
        )
        segments = (Segment(0.0, 5.0, "Hello"),)
        transcript = Transcript(video=video, text="Hello", segments=segments)
        assert transcript.text == "Hello"
        assert len(transcript.segments) == 1

    def test_segments_is_tuple(self):
        video = VideoInfo(
            video_id="abc", title="T", channel="C",
            url="http://y.com", duration_seconds=60, playlist_title=None,
        )
        transcript = Transcript(video=video, text="Hi", segments=(Segment(0.0, 1.0, "Hi"),))
        assert isinstance(transcript.segments, tuple)


class TestJob:
    def test_creation(self):
        video = VideoInfo(
            video_id="abc", title="T", channel="C",
            url="http://y.com", duration_seconds=60, playlist_title=None,
        )
        job = Job(
            job_id="job-1",
            status=JobStatus.QUEUED,
            videos=(video,),
            completed_count=0,
            error=None,
        )
        assert job.status == JobStatus.QUEUED
        assert isinstance(job.videos, tuple)
