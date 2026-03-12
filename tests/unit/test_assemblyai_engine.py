"""Tests for AssemblyAI cloud transcription engine. assemblyai SDK is fully mocked."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yt_transcribe.assemblyai_engine import transcribe
from yt_transcribe.exceptions import TranscriptionError
from yt_transcribe.models import Segment


# -- Mock helpers --

def _make_mock_utterance(start_ms: int, end_ms: int, text: str) -> MagicMock:
    """Create a mock AssemblyAI word/utterance with timing in milliseconds."""
    utterance = MagicMock()
    utterance.start = start_ms
    utterance.end = end_ms
    utterance.text = text
    return utterance


class TestTranscribe:
    @patch("yt_transcribe.assemblyai_engine.aai")
    def test_returns_tuple_of_segments(self, mock_aai: MagicMock, tmp_path: Path):
        """transcribe returns an immutable tuple of Segment dataclasses."""
        audio_file = tmp_path / "test.m4a"
        audio_file.write_bytes(b"fake")

        mock_transcript = MagicMock()
        mock_transcript.status = "completed"
        mock_transcript.error = None
        mock_transcript.utterances = [
            _make_mock_utterance(0, 5000, "Hello world"),
            _make_mock_utterance(5000, 10000, "Second sentence"),
        ]

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = mock_transcript
        mock_aai.Transcriber.return_value = mock_transcriber

        result = transcribe(audio_file, "test-api-key")

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Segment)
        assert result[0].start_seconds == 0.0
        assert result[0].end_seconds == 5.0
        assert result[0].text == "Hello world"

    @patch("yt_transcribe.assemblyai_engine.aai")
    def test_sets_api_key(self, mock_aai: MagicMock, tmp_path: Path):
        """transcribe sets the AssemblyAI API key before calling the SDK."""
        audio_file = tmp_path / "test.m4a"
        audio_file.write_bytes(b"fake")

        mock_transcript = MagicMock()
        mock_transcript.status = "completed"
        mock_transcript.error = None
        mock_transcript.utterances = []
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = mock_transcript
        mock_aai.Transcriber.return_value = mock_transcriber

        transcribe(audio_file, "my-secret-key")

        mock_aai.settings.api_key = "my-secret-key"

    @patch("yt_transcribe.assemblyai_engine.aai")
    def test_raises_transcription_error_on_failure(self, mock_aai: MagicMock, tmp_path: Path):
        """transcribe raises TranscriptionError when AssemblyAI reports an error."""
        audio_file = tmp_path / "test.m4a"
        audio_file.write_bytes(b"fake")

        mock_transcript = MagicMock()
        mock_transcript.status = "error"
        mock_transcript.error = "Audio too short"
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = mock_transcript
        mock_aai.Transcriber.return_value = mock_transcriber

        with pytest.raises(TranscriptionError, match="Audio too short"):
            transcribe(audio_file, "test-api-key")

    @patch("yt_transcribe.assemblyai_engine.aai")
    def test_raises_transcription_error_on_sdk_exception(
        self, mock_aai: MagicMock, tmp_path: Path
    ):
        """transcribe raises TranscriptionError when the SDK throws an exception."""
        audio_file = tmp_path / "test.m4a"
        audio_file.write_bytes(b"fake")

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.side_effect = RuntimeError("Network error")
        mock_aai.Transcriber.return_value = mock_transcriber

        with pytest.raises(TranscriptionError, match="Network error"):
            transcribe(audio_file, "test-api-key")

    @patch("yt_transcribe.assemblyai_engine.aai")
    def test_empty_utterances_returns_empty_tuple(self, mock_aai: MagicMock, tmp_path: Path):
        """transcribe returns empty tuple when no utterances are returned."""
        audio_file = tmp_path / "test.m4a"
        audio_file.write_bytes(b"fake")

        mock_transcript = MagicMock()
        mock_transcript.status = "completed"
        mock_transcript.error = None
        mock_transcript.utterances = None
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = mock_transcript
        mock_aai.Transcriber.return_value = mock_transcriber

        result = transcribe(audio_file, "test-api-key")

        assert result == ()
