"""3-tier transcription orchestrator: captions -> AssemblyAI -> Whisper."""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from yt_transcribe import assemblyai_engine, download, whisper_engine
from yt_transcribe.config import get_assemblyai_api_key
from yt_transcribe.exceptions import TranscriptionError
from yt_transcribe.models import (
    Config,
    Segment,
    Transcript,
    TranscriptionStrategy,
    VideoInfo,
)

logger = logging.getLogger(__name__)

# Interval in seconds for inserting timestamps into formatted text
_TIMESTAMP_INTERVAL = 300  # 5 minutes


def transcribe_video(
    video_info: VideoInfo,
    config: Config,
    progress_callback: Callable[[float], None] | None = None,
) -> Transcript:
    """Transcribe a video using the 3-tier cascade strategy.

    Cascade order (for AUTO strategy):
    1. YouTube captions (free, instant)
    2. AssemblyAI cloud (fast, requires API key)
    3. Whisper local CPU (free, slow)

    CLOUD strategy skips captions, goes straight to AssemblyAI.
    LOCAL strategy skips captions and cloud, goes straight to Whisper.

    Args:
        video_info: Metadata about the video to transcribe.
        config: Application configuration with strategy and model settings.
        progress_callback: Optional callback receiving progress float (0.0 to 1.0).

    Returns:
        Immutable Transcript with formatted text and raw segments.

    Raises:
        TranscriptionError: If all available transcription tiers fail.
    """
    strategy = config.transcription_strategy

    # Tier 1: Try captions (AUTO only)
    if strategy == TranscriptionStrategy.AUTO:
        segments = _try_captions(video_info.url)
        if segments is not None:
            text = _format_text(segments)
            return Transcript(video=video_info, text=text, segments=segments)

    # Tier 2 and 3 require audio download
    if strategy == TranscriptionStrategy.AUTO:
        segments = _try_cloud_then_local(video_info, config, progress_callback)
    elif strategy == TranscriptionStrategy.CLOUD:
        segments = _try_cloud_only(video_info, config)
    elif strategy == TranscriptionStrategy.LOCAL:
        segments = _try_local_only(video_info, config, progress_callback)
    else:
        raise TranscriptionError(f"Unknown strategy: {strategy}")

    text = _format_text(segments)
    return Transcript(video=video_info, text=text, segments=segments)


def _try_captions(url: str) -> tuple[Segment, ...] | None:
    """Attempt to extract YouTube captions. Returns None if unavailable.

    Args:
        url: YouTube video URL.

    Returns:
        Tuple of Segments if captions exist, None otherwise.
    """
    try:
        return download.get_captions(url)
    except Exception:
        logger.debug("Caption extraction failed for %s", url)
        return None


def _try_cloud_then_local(
    video_info: VideoInfo,
    config: Config,
    progress_callback: Callable[[float], None] | None = None,
) -> tuple[Segment, ...]:
    """Try AssemblyAI first, fall back to Whisper on failure.

    Args:
        video_info: Video metadata.
        config: Application configuration.
        progress_callback: Optional progress callback.

    Returns:
        Tuple of Segment dataclasses.

    Raises:
        TranscriptionError: If both cloud and local transcription fail.
    """
    temp_dir = tempfile.mkdtemp(prefix="yt-transcribe-")
    try:
        audio_path = download.download_audio(video_info.url, Path(temp_dir))

        # Try AssemblyAI if API key is available
        api_key = get_assemblyai_api_key()
        if api_key:
            try:
                return assemblyai_engine.transcribe(audio_path, api_key)
            except TranscriptionError:
                logger.warning("AssemblyAI failed for %s, falling back to Whisper", video_info.url)

        # Fall back to Whisper
        return whisper_engine.transcribe(audio_path, config.whisper_model, progress_callback)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _try_cloud_only(video_info: VideoInfo, config: Config) -> tuple[Segment, ...]:
    """Transcribe using AssemblyAI only. Requires API key.

    Args:
        video_info: Video metadata.
        config: Application configuration.

    Returns:
        Tuple of Segment dataclasses.

    Raises:
        TranscriptionError: If no API key or AssemblyAI fails.
    """
    api_key = get_assemblyai_api_key()
    if not api_key:
        raise TranscriptionError("Cloud strategy requires an AssemblyAI API key")

    temp_dir = tempfile.mkdtemp(prefix="yt-transcribe-")
    try:
        audio_path = download.download_audio(video_info.url, Path(temp_dir))
        return assemblyai_engine.transcribe(audio_path, api_key)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _try_local_only(
    video_info: VideoInfo,
    config: Config,
    progress_callback: Callable[[float], None] | None = None,
) -> tuple[Segment, ...]:
    """Transcribe using local Whisper only.

    Args:
        video_info: Video metadata.
        config: Application configuration.
        progress_callback: Optional progress callback.

    Returns:
        Tuple of Segment dataclasses.

    Raises:
        TranscriptionError: If Whisper fails.
    """
    temp_dir = tempfile.mkdtemp(prefix="yt-transcribe-")
    try:
        audio_path = download.download_audio(video_info.url, Path(temp_dir))
        return whisper_engine.transcribe(audio_path, config.whisper_model, progress_callback)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _format_text(segments: tuple[Segment, ...]) -> str:
    """Format segments into readable text with 5-minute interval timestamps.

    Inserts [MM:SS] markers at every 5-minute boundary. Text flows naturally
    between timestamps with no marker at the start (00:00).

    Args:
        segments: Tuple of Segment dataclasses to format.

    Returns:
        Formatted transcript text string.
    """
    if not segments:
        return ""

    parts: list[str] = []
    next_timestamp = _TIMESTAMP_INTERVAL  # First timestamp at 5:00, not 0:00

    for segment in segments:
        # Insert timestamp marker if this segment crosses a 5-minute boundary
        while segment.start_seconds >= next_timestamp:
            minutes = int(next_timestamp) // 60
            seconds = int(next_timestamp) % 60
            parts.append(f"\n\n[{minutes:02d}:{seconds:02d}]")
            next_timestamp += _TIMESTAMP_INTERVAL

        parts.append(segment.text)

    return "\n".join(parts)
