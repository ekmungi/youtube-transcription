"""Tests for 3-tier transcription orchestrator. All engines and download are mocked."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yt_transcribe.download import VideoData
from yt_transcribe.exceptions import TranscriptionError
from yt_transcribe.models import (
    Config,
    Segment,
    Transcript,
    TranscriptionStrategy,
    VideoInfo,
    WhisperModel,
)
from yt_transcribe.transcribe import transcribe_video, transcribe_video_fast


# -- Fixtures --

SAMPLE_VIDEO = VideoInfo(
    video_id="abc123",
    title="Test Video",
    channel="Test Channel",
    url="https://www.youtube.com/watch?v=abc123",
    duration_seconds=600,
    playlist_title=None,
)

SAMPLE_SEGMENTS = (
    Segment(start_seconds=0.0, end_seconds=5.0, text="Hello world"),
    Segment(start_seconds=5.0, end_seconds=10.0, text="Second line"),
)

AUTO_CONFIG = Config(
    obsidian_vault_path="/vault",
    transcript_folder="Transcripts",
    transcription_strategy=TranscriptionStrategy.AUTO,
    whisper_model=WhisperModel.BASE,
    async_threshold_seconds=180,
    parallel_enabled=False,
)

CLOUD_CONFIG = Config(
    obsidian_vault_path="/vault",
    transcript_folder="Transcripts",
    transcription_strategy=TranscriptionStrategy.CLOUD,
    whisper_model=WhisperModel.BASE,
    async_threshold_seconds=180,
    parallel_enabled=False,
)

LOCAL_CONFIG = Config(
    obsidian_vault_path="/vault",
    transcript_folder="Transcripts",
    transcription_strategy=TranscriptionStrategy.LOCAL,
    whisper_model=WhisperModel.BASE,
    async_threshold_seconds=180,
    parallel_enabled=False,
)

SAMPLE_VIDEO_DATA = VideoData(
    video_info=SAMPLE_VIDEO,
    captions=SAMPLE_SEGMENTS,
    audio_url="https://audio.youtube.com/stream/abc123",
    raw_info={"id": "abc123"},
)

SAMPLE_VIDEO_DATA_NO_CAPTIONS = VideoData(
    video_info=SAMPLE_VIDEO,
    captions=None,
    audio_url="https://audio.youtube.com/stream/abc123",
    raw_info={"id": "abc123"},
)

SAMPLE_VIDEO_DATA_NO_URL = VideoData(
    video_info=SAMPLE_VIDEO,
    captions=None,
    audio_url=None,
    raw_info={"id": "abc123"},
)


# -- transcribe_video_fast tests (optimized path) --

class TestTranscribeVideoFastAutoStrategy:
    """Tests for the optimized fast path with AUTO strategy."""

    def test_uses_pre_fetched_captions(self):
        """Fast path uses captions from VideoData without any network call."""
        result = transcribe_video_fast(SAMPLE_VIDEO_DATA, AUTO_CONFIG)

        assert isinstance(result, Transcript)
        assert result.video == SAMPLE_VIDEO
        assert result.segments == SAMPLE_SEGMENTS
        assert "Hello world" in result.text

    @patch("yt_transcribe.transcribe.assemblyai_engine")
    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value="test-key")
    def test_uses_url_transcription_when_no_captions(
        self, mock_get_key: MagicMock, mock_aai: MagicMock
    ):
        """Fast path uses AssemblyAI URL transcription when captions unavailable."""
        mock_aai.transcribe_url.return_value = SAMPLE_SEGMENTS

        result = transcribe_video_fast(SAMPLE_VIDEO_DATA_NO_CAPTIONS, AUTO_CONFIG)

        assert isinstance(result, Transcript)
        mock_aai.transcribe_url.assert_called_once_with(
            "https://audio.youtube.com/stream/abc123", "test-key"
        )

    @patch("yt_transcribe.transcribe.whisper_engine")
    @patch("yt_transcribe.transcribe.download")
    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value=None)
    def test_falls_back_to_whisper_when_no_api_key(
        self, mock_get_key: MagicMock, mock_download: MagicMock, mock_whisper: MagicMock,
        tmp_path: Path,
    ):
        """Fast path falls back to download+Whisper when no API key."""
        mock_download.download_audio.return_value = tmp_path / "audio.m4a"
        mock_whisper.transcribe.return_value = SAMPLE_SEGMENTS

        result = transcribe_video_fast(SAMPLE_VIDEO_DATA_NO_CAPTIONS, AUTO_CONFIG)

        assert isinstance(result, Transcript)
        mock_whisper.transcribe.assert_called_once()

    @patch("yt_transcribe.transcribe.whisper_engine")
    @patch("yt_transcribe.transcribe.download")
    @patch("yt_transcribe.transcribe.assemblyai_engine")
    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value="test-key")
    def test_falls_back_to_download_when_url_transcription_fails(
        self, mock_get_key: MagicMock, mock_aai: MagicMock,
        mock_download: MagicMock, mock_whisper: MagicMock,
        tmp_path: Path,
    ):
        """Fast path falls back to download+Whisper when URL transcription fails."""
        mock_aai.transcribe_url.side_effect = TranscriptionError("URL fetch failed")
        # File upload also fails, forcing Whisper fallback
        mock_aai.transcribe.side_effect = TranscriptionError("Upload also failed")
        mock_download.download_audio.return_value = tmp_path / "audio.m4a"
        mock_whisper.transcribe.return_value = SAMPLE_SEGMENTS

        result = transcribe_video_fast(SAMPLE_VIDEO_DATA_NO_CAPTIONS, AUTO_CONFIG)

        assert isinstance(result, Transcript)
        mock_whisper.transcribe.assert_called_once()


class TestTranscribeVideoFastCloudStrategy:
    """Tests for fast path with CLOUD strategy."""

    @patch("yt_transcribe.transcribe.assemblyai_engine")
    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value="test-key")
    def test_uses_url_transcription(self, mock_get_key: MagicMock, mock_aai: MagicMock):
        """Cloud strategy uses URL transcription directly."""
        mock_aai.transcribe_url.return_value = SAMPLE_SEGMENTS

        result = transcribe_video_fast(SAMPLE_VIDEO_DATA_NO_CAPTIONS, CLOUD_CONFIG)

        assert isinstance(result, Transcript)
        mock_aai.transcribe_url.assert_called_once()

    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value=None)
    def test_raises_when_no_api_key(self, mock_get_key: MagicMock):
        """Cloud strategy raises when no API key available."""
        with pytest.raises(TranscriptionError, match="API key"):
            transcribe_video_fast(SAMPLE_VIDEO_DATA_NO_CAPTIONS, CLOUD_CONFIG)

    @patch("yt_transcribe.transcribe.assemblyai_engine")
    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value="test-key")
    def test_raises_when_url_transcription_fails(
        self, mock_get_key: MagicMock, mock_aai: MagicMock
    ):
        """Cloud strategy raises when URL transcription fails (no fallback)."""
        mock_aai.transcribe_url.side_effect = TranscriptionError("Failed")

        with pytest.raises(TranscriptionError):
            transcribe_video_fast(SAMPLE_VIDEO_DATA_NO_CAPTIONS, CLOUD_CONFIG)


class TestTranscribeVideoFastLocalStrategy:
    """Tests for fast path with LOCAL strategy."""

    @patch("yt_transcribe.transcribe.whisper_engine")
    @patch("yt_transcribe.transcribe.download")
    def test_downloads_and_uses_whisper(
        self, mock_download: MagicMock, mock_whisper: MagicMock, tmp_path: Path
    ):
        """Local strategy downloads audio and uses Whisper."""
        mock_download.download_audio.return_value = tmp_path / "audio.m4a"
        mock_whisper.transcribe.return_value = SAMPLE_SEGMENTS

        result = transcribe_video_fast(SAMPLE_VIDEO_DATA_NO_CAPTIONS, LOCAL_CONFIG)

        assert isinstance(result, Transcript)
        mock_whisper.transcribe.assert_called_once()


# -- Legacy transcribe_video tests --

class TestTranscribeVideoAutoStrategy:
    @patch("yt_transcribe.transcribe.download")
    def test_uses_captions_when_available(self, mock_download: MagicMock):
        """Auto strategy uses captions as first tier when they exist."""
        mock_download.get_captions.return_value = SAMPLE_SEGMENTS

        result = transcribe_video(SAMPLE_VIDEO, AUTO_CONFIG)

        assert isinstance(result, Transcript)
        assert result.video == SAMPLE_VIDEO
        assert result.segments == SAMPLE_SEGMENTS
        assert "Hello world" in result.text
        mock_download.download_audio.assert_not_called()

    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value="test-key")
    @patch("yt_transcribe.transcribe.assemblyai_engine")
    @patch("yt_transcribe.transcribe.download")
    def test_falls_back_to_assemblyai_when_no_captions(
        self,
        mock_download: MagicMock,
        mock_aai_engine: MagicMock,
        mock_get_key: MagicMock,
        tmp_path: Path,
    ):
        """Auto strategy falls back to AssemblyAI when captions are unavailable."""
        mock_download.get_captions.return_value = None
        mock_download.download_audio.return_value = tmp_path / "audio.m4a"
        mock_aai_engine.transcribe.return_value = SAMPLE_SEGMENTS

        result = transcribe_video(SAMPLE_VIDEO, AUTO_CONFIG)

        assert isinstance(result, Transcript)
        mock_aai_engine.transcribe.assert_called_once()
        assert result.segments == SAMPLE_SEGMENTS

    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value=None)
    @patch("yt_transcribe.transcribe.whisper_engine")
    @patch("yt_transcribe.transcribe.download")
    def test_falls_back_to_whisper_when_no_api_key(
        self,
        mock_download: MagicMock,
        mock_whisper: MagicMock,
        mock_get_key: MagicMock,
        tmp_path: Path,
    ):
        """Auto strategy falls back to Whisper when no AssemblyAI key is available."""
        mock_download.get_captions.return_value = None
        mock_download.download_audio.return_value = tmp_path / "audio.m4a"
        mock_whisper.transcribe.return_value = SAMPLE_SEGMENTS

        result = transcribe_video(SAMPLE_VIDEO, AUTO_CONFIG)

        assert isinstance(result, Transcript)
        mock_whisper.transcribe.assert_called_once()

    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value="test-key")
    @patch("yt_transcribe.transcribe.whisper_engine")
    @patch("yt_transcribe.transcribe.assemblyai_engine")
    @patch("yt_transcribe.transcribe.download")
    def test_falls_back_to_whisper_when_assemblyai_fails(
        self,
        mock_download: MagicMock,
        mock_aai_engine: MagicMock,
        mock_whisper: MagicMock,
        mock_get_key: MagicMock,
        tmp_path: Path,
    ):
        """Auto strategy falls back to Whisper when AssemblyAI raises an error."""
        mock_download.get_captions.return_value = None
        mock_download.download_audio.return_value = tmp_path / "audio.m4a"
        mock_aai_engine.transcribe.side_effect = TranscriptionError("API failed")
        mock_whisper.transcribe.return_value = SAMPLE_SEGMENTS

        result = transcribe_video(SAMPLE_VIDEO, AUTO_CONFIG)

        assert isinstance(result, Transcript)
        mock_whisper.transcribe.assert_called_once()


class TestTranscribeVideoCloudStrategy:
    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value="test-key")
    @patch("yt_transcribe.transcribe.assemblyai_engine")
    @patch("yt_transcribe.transcribe.download")
    def test_skips_captions_uses_assemblyai(
        self,
        mock_download: MagicMock,
        mock_aai_engine: MagicMock,
        mock_get_key: MagicMock,
        tmp_path: Path,
    ):
        """Cloud strategy skips captions and goes directly to AssemblyAI."""
        mock_download.download_audio.return_value = tmp_path / "audio.m4a"
        mock_aai_engine.transcribe.return_value = SAMPLE_SEGMENTS

        result = transcribe_video(SAMPLE_VIDEO, CLOUD_CONFIG)

        assert isinstance(result, Transcript)
        mock_download.get_captions.assert_not_called()
        mock_aai_engine.transcribe.assert_called_once()

    @patch("yt_transcribe.transcribe.get_assemblyai_api_key", return_value=None)
    @patch("yt_transcribe.transcribe.download")
    def test_raises_when_no_api_key(self, mock_download: MagicMock, mock_get_key: MagicMock):
        """Cloud strategy raises TranscriptionError when no API key is available."""
        with pytest.raises(TranscriptionError, match="API key"):
            transcribe_video(SAMPLE_VIDEO, CLOUD_CONFIG)


class TestTranscribeVideoLocalStrategy:
    @patch("yt_transcribe.transcribe.whisper_engine")
    @patch("yt_transcribe.transcribe.download")
    def test_skips_captions_and_cloud_uses_whisper(
        self,
        mock_download: MagicMock,
        mock_whisper: MagicMock,
        tmp_path: Path,
    ):
        """Local strategy skips captions and cloud, goes directly to Whisper."""
        mock_download.download_audio.return_value = tmp_path / "audio.m4a"
        mock_whisper.transcribe.return_value = SAMPLE_SEGMENTS

        result = transcribe_video(SAMPLE_VIDEO, LOCAL_CONFIG)

        assert isinstance(result, Transcript)
        mock_download.get_captions.assert_not_called()
        mock_whisper.transcribe.assert_called_once()


class TestTranscribeVideoTextFormatting:
    @patch("yt_transcribe.transcribe.download")
    def test_text_includes_timestamps_at_five_minute_intervals(
        self, mock_download: MagicMock
    ):
        """Formatted text includes [MM:SS] timestamps at 5-minute boundaries."""
        segments = (
            Segment(0.0, 60.0, "Intro text here."),
            Segment(60.0, 300.0, "More content before five minutes."),
            Segment(300.0, 360.0, "Content after five minutes."),
            Segment(360.0, 600.0, "Even more content."),
            Segment(600.0, 660.0, "At ten minutes."),
        )
        mock_download.get_captions.return_value = segments

        result = transcribe_video(SAMPLE_VIDEO, AUTO_CONFIG)

        assert "[05:00]" in result.text
        assert "[10:00]" in result.text


class TestTranscribeVideoCleanup:
    @patch("yt_transcribe.transcribe.whisper_engine")
    @patch("yt_transcribe.transcribe.download")
    @patch("yt_transcribe.transcribe.tempfile")
    def test_temp_dir_cleaned_up_on_success(
        self,
        mock_tempfile: MagicMock,
        mock_download: MagicMock,
        mock_whisper: MagicMock,
    ):
        """Temporary audio directory is cleaned up after successful transcription."""
        mock_temp_dir = "/tmp/yt-transcribe-abc"
        mock_tempfile.mkdtemp.return_value = mock_temp_dir
        mock_download.download_audio.return_value = Path(mock_temp_dir) / "audio.m4a"
        mock_whisper.transcribe.return_value = SAMPLE_SEGMENTS

        result = transcribe_video(SAMPLE_VIDEO, LOCAL_CONFIG)

        assert isinstance(result, Transcript)

    @patch("yt_transcribe.transcribe.whisper_engine")
    @patch("yt_transcribe.transcribe.download")
    @patch("yt_transcribe.transcribe.tempfile")
    def test_temp_dir_cleaned_up_on_failure(
        self,
        mock_tempfile: MagicMock,
        mock_download: MagicMock,
        mock_whisper: MagicMock,
    ):
        """Temporary audio directory is cleaned up even when transcription fails."""
        mock_temp_dir = "/tmp/yt-transcribe-abc"
        mock_tempfile.mkdtemp.return_value = mock_temp_dir
        mock_download.download_audio.return_value = Path(mock_temp_dir) / "audio.m4a"
        mock_whisper.transcribe.side_effect = TranscriptionError("Failed")

        with pytest.raises(TranscriptionError):
            transcribe_video(SAMPLE_VIDEO, LOCAL_CONFIG)
