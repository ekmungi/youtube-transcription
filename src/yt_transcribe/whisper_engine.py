"""Local Whisper transcription engine using faster-whisper (CTranslate2)."""

from __future__ import annotations

import logging
from pathlib import Path

from faster_whisper import WhisperModel

from yt_transcribe.exceptions import TranscriptionError
from yt_transcribe.models import Segment
from yt_transcribe.models import WhisperModel as WhisperModelSize

logger = logging.getLogger(__name__)


def transcribe(
    audio_path: Path,
    model_size: WhisperModelSize,
) -> tuple[Segment, ...]:
    """Transcribe an audio file using faster-whisper on CPU.

    Args:
        audio_path: Path to the audio file to transcribe.
        model_size: Whisper model size (tiny, base, small, medium).

    Returns:
        Tuple of Segment dataclasses with timestamps and text.

    Raises:
        TranscriptionError: If faster-whisper fails during transcription.
    """
    try:
        model = WhisperModel(model_size.value, device="cpu", compute_type="int8")
        raw_segments, info = model.transcribe(str(audio_path))
    except Exception as exc:
        raise TranscriptionError(f"Whisper transcription failed: {exc}") from exc

    segments: list[Segment] = []

    try:
        for raw_seg in raw_segments:
            segment = Segment(
                start_seconds=raw_seg.start,
                end_seconds=raw_seg.end,
                text=raw_seg.text.strip(),
            )
            segments.append(segment)
    except Exception as exc:
        raise TranscriptionError(f"Error processing Whisper segments: {exc}") from exc

    return tuple(segments)
