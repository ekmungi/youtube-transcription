"""AssemblyAI cloud transcription engine using the assemblyai Python SDK."""

from __future__ import annotations

import logging
from pathlib import Path

import assemblyai as aai
from tenacity import retry, stop_after_attempt, wait_exponential

from yt_transcribe.exceptions import TranscriptionError
from yt_transcribe.models import Segment

logger = logging.getLogger(__name__)

# Milliseconds to seconds conversion factor
_MS_TO_SEC = 1000.0


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def _submit_transcription(transcriber: aai.Transcriber, audio_path: str) -> aai.Transcript:
    """Submit audio to AssemblyAI with retry logic.

    Args:
        transcriber: Configured AssemblyAI transcriber instance.
        audio_path: Path to the audio file.

    Returns:
        AssemblyAI Transcript result object.
    """
    return transcriber.transcribe(audio_path)


def transcribe(audio_path: Path, api_key: str) -> tuple[Segment, ...]:
    """Transcribe an audio file using AssemblyAI cloud service.

    Uploads the audio file to AssemblyAI, waits for completion, and converts
    the result into immutable Segment tuples. Retries upload/poll failures
    3 times with exponential backoff.

    Args:
        audio_path: Path to the audio file to transcribe.
        api_key: AssemblyAI API key for authentication.

    Returns:
        Tuple of Segment dataclasses with timestamps and text.

    Raises:
        TranscriptionError: If AssemblyAI returns an error or the SDK fails.
    """
    aai.settings.api_key = api_key

    try:
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(speaker_labels=True)
        transcript = _submit_transcription(transcriber, str(audio_path))
    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(f"AssemblyAI transcription failed: {exc}") from exc

    if transcript.status == "error" or transcript.error:
        raise TranscriptionError(
            f"AssemblyAI error: {transcript.error or 'Unknown error'}"
        )

    utterances = transcript.utterances
    if not utterances:
        return ()

    return tuple(
        Segment(
            start_seconds=u.start / _MS_TO_SEC,
            end_seconds=u.end / _MS_TO_SEC,
            text=u.text.strip(),
        )
        for u in utterances
    )
