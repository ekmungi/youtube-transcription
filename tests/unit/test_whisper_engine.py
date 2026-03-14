"""Tests for local Whisper transcription engine. faster-whisper is fully mocked."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yt_transcribe.models import Segment, WhisperModel
from yt_transcribe.whisper_engine import transcribe


# -- Mock segment helper --

def _make_mock_segment(start: float, end: float, text: str) -> MagicMock:
    """Create a mock faster-whisper segment with the given attributes."""
    seg = MagicMock()
    seg.start = start
    seg.end = end
    seg.text = text
    return seg


class TestTranscribe:
    @patch("yt_transcribe.whisper_engine.WhisperModel")
    def test_returns_tuple_of_segments(self, mock_model_cls: MagicMock, tmp_path: Path):
        """transcribe returns an immutable tuple of Segment dataclasses."""
        audio_file = tmp_path / "test.m4a"
        audio_file.write_bytes(b"fake")

        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model

        mock_segments = [
            _make_mock_segment(0.0, 5.0, "Hello world"),
            _make_mock_segment(5.0, 10.0, "Second sentence"),
        ]
        mock_info = MagicMock()
        mock_info.duration = 10.0
        mock_model.transcribe.return_value = (iter(mock_segments), mock_info)

        result = transcribe(audio_file, WhisperModel.BASE)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Segment)
        assert result[0].start_seconds == 0.0
        assert result[0].text == "Hello world"
        assert result[1].text == "Second sentence"

    @patch("yt_transcribe.whisper_engine.WhisperModel")
    def test_empty_audio_returns_empty_tuple(self, mock_model_cls: MagicMock, tmp_path: Path):
        """transcribe returns empty tuple when no speech is detected."""
        audio_file = tmp_path / "silence.m4a"
        audio_file.write_bytes(b"fake")

        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model

        mock_info = MagicMock()
        mock_info.duration = 5.0
        mock_model.transcribe.return_value = (iter([]), mock_info)

        result = transcribe(audio_file, WhisperModel.BASE)

        assert result == ()

    @patch("yt_transcribe.whisper_engine.WhisperModel")
    def test_uses_correct_model_size(self, mock_model_cls: MagicMock, tmp_path: Path):
        """transcribe initializes the Whisper model with the correct size string."""
        audio_file = tmp_path / "test.m4a"
        audio_file.write_bytes(b"fake")

        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        mock_info = MagicMock()
        mock_info.duration = 1.0
        mock_model.transcribe.return_value = (iter([]), mock_info)

        transcribe(audio_file, WhisperModel.SMALL)

        mock_model_cls.assert_called_once_with("small", device="cpu", compute_type="int8")

    @patch("yt_transcribe.whisper_engine.WhisperModel")
    def test_raises_on_transcription_failure(self, mock_model_cls: MagicMock, tmp_path: Path):
        """transcribe raises TranscriptionError when faster-whisper fails."""
        audio_file = tmp_path / "test.m4a"
        audio_file.write_bytes(b"fake")

        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        mock_model.transcribe.side_effect = RuntimeError("Model failed")

        from yt_transcribe.exceptions import TranscriptionError
        with pytest.raises(TranscriptionError):
            transcribe(audio_file, WhisperModel.BASE)
