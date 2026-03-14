"""3-tier transcription orchestrator: captions -> AssemblyAI -> Whisper.

Optimized pipeline uses a single yt-dlp extract_info call via VideoData,
and passes audio URLs directly to AssemblyAI to skip download/upload.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from yt_transcribe import assemblyai_engine, download, whisper_engine
from yt_transcribe.config import get_assemblyai_api_key
from yt_transcribe.download import VideoData
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


def transcribe_video_fast(
    video_data: VideoData,
    config: Config,
    phase_callback: Callable[[str], None] | None = None,
) -> Transcript:
    """Transcribe a video using pre-fetched VideoData (optimized path).

    Uses the single-call VideoData to avoid redundant yt-dlp calls. Passes
    audio URLs directly to AssemblyAI when possible to skip download/upload.

    Args:
        video_data: Pre-fetched video metadata, captions, and audio URL.
        config: Application configuration with strategy and model settings.
        phase_callback: Optional callback receiving status text.

    Returns:
        Immutable Transcript with formatted text and raw segments.

    Raises:
        TranscriptionError: If all available transcription tiers fail.
    """
    strategy = config.transcription_strategy
    _report = phase_callback or (lambda _: None)
    video_info = video_data.video_info

    # Tier 1: Use pre-fetched captions (AUTO and CAPTIONS strategies)
    if strategy in (TranscriptionStrategy.AUTO, TranscriptionStrategy.CAPTIONS):
        _report("checking captions...")
        if video_data.captions is not None:
            text = _format_text(video_data.captions)
            return Transcript(video=video_info, text=text, segments=video_data.captions)
        if strategy == TranscriptionStrategy.CAPTIONS:
            raise TranscriptionError(
                f"No YouTube captions available for: {video_info.title}"
            )

    # Tier 2: AssemblyAI via URL (no download/upload needed)
    if strategy in (TranscriptionStrategy.AUTO, TranscriptionStrategy.CLOUD):
        api_key = get_assemblyai_api_key()
        if api_key and video_data.audio_url:
            try:
                _report("transcribing (cloud, direct URL)...")
                segments = assemblyai_engine.transcribe_url(video_data.audio_url, api_key)
                text = _format_text(segments)
                return Transcript(video=video_info, text=text, segments=segments)
            except TranscriptionError:
                if strategy == TranscriptionStrategy.CLOUD:
                    raise
                logger.warning(
                    "AssemblyAI URL transcription failed for %s, trying file upload",
                    video_info.url,
                )

        # Cloud-only with no API key
        if strategy == TranscriptionStrategy.CLOUD and not api_key:
            raise TranscriptionError("Cloud strategy requires an AssemblyAI API key")

    # Tier 3: Download audio + file-based transcription (AssemblyAI upload or Whisper)
    segments = _download_and_transcribe(video_info, config, _report)
    text = _format_text(segments)
    return Transcript(video=video_info, text=text, segments=segments)


def transcribe_video(
    video_info: VideoInfo,
    config: Config,
    phase_callback: Callable[[str], None] | None = None,
) -> Transcript:
    """Transcribe a video using the 3-tier cascade strategy (legacy path).

    This is the backward-compatible entry point. For better performance,
    use transcribe_video_fast() with a pre-fetched VideoData object.

    Args:
        video_info: Metadata about the video to transcribe.
        config: Application configuration with strategy and model settings.
        phase_callback: Optional callback receiving status text.

    Returns:
        Immutable Transcript with formatted text and raw segments.

    Raises:
        TranscriptionError: If all available transcription tiers fail.
    """
    strategy = config.transcription_strategy
    _report = phase_callback or (lambda _: None)

    # Tier 1: Try captions (AUTO and CAPTIONS strategies)
    if strategy in (TranscriptionStrategy.AUTO, TranscriptionStrategy.CAPTIONS):
        _report("fetching captions...")
        segments = _try_captions(video_info.url)
        if segments is not None:
            text = _format_text(segments)
            return Transcript(video=video_info, text=text, segments=segments)
        if strategy == TranscriptionStrategy.CAPTIONS:
            raise TranscriptionError(
                f"No YouTube captions available for: {video_info.title}"
            )

    # Tier 2 and 3 require audio download
    if strategy == TranscriptionStrategy.AUTO:
        segments = _try_cloud_then_local(video_info, config, _report)
    elif strategy == TranscriptionStrategy.CLOUD:
        segments = _try_cloud_only(video_info, config, _report)
    elif strategy == TranscriptionStrategy.LOCAL:
        segments = _try_local_only(video_info, config, _report)
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


def _download_and_transcribe(
    video_info: VideoInfo,
    config: Config,
    report: Callable[[str], None],
) -> tuple[Segment, ...]:
    """Download audio and transcribe using file-based engines.

    Tries AssemblyAI file upload first (if API key available), then Whisper.

    Args:
        video_info: Video metadata.
        config: Application configuration.
        report: Phase status callback.

    Returns:
        Tuple of Segment dataclasses.

    Raises:
        TranscriptionError: If all transcription methods fail.
    """
    strategy = config.transcription_strategy
    temp_dir = tempfile.mkdtemp(prefix="yt-transcribe-")
    try:
        report("downloading audio...")
        audio_path = download.download_audio(
            video_info.url, Path(temp_dir), config.ffmpeg_location,
        )

        # Try AssemblyAI file upload (AUTO or CLOUD strategies)
        if strategy in (TranscriptionStrategy.AUTO, TranscriptionStrategy.CLOUD):
            api_key = get_assemblyai_api_key()
            if api_key:
                try:
                    report("transcribing (cloud, file upload)...")
                    return assemblyai_engine.transcribe(audio_path, api_key)
                except TranscriptionError:
                    if strategy == TranscriptionStrategy.CLOUD:
                        raise
                    logger.warning(
                        "AssemblyAI file upload failed for %s, falling back to Whisper",
                        video_info.url,
                    )
            elif strategy == TranscriptionStrategy.CLOUD:
                raise TranscriptionError("Cloud strategy requires an AssemblyAI API key")

        # Local Whisper fallback
        report("transcribing (local)...")
        return whisper_engine.transcribe(audio_path, config.whisper_model)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _try_cloud_then_local(
    video_info: VideoInfo,
    config: Config,
    report: Callable[[str], None],
) -> tuple[Segment, ...]:
    """Try AssemblyAI first, fall back to Whisper on failure.

    Args:
        video_info: Video metadata.
        config: Application configuration.
        report: Phase status callback.

    Returns:
        Tuple of Segment dataclasses.

    Raises:
        TranscriptionError: If both cloud and local transcription fail.
    """
    temp_dir = tempfile.mkdtemp(prefix="yt-transcribe-")
    try:
        report("downloading audio...")
        audio_path = download.download_audio(
            video_info.url, Path(temp_dir), config.ffmpeg_location,
        )

        # Try AssemblyAI if API key is available
        api_key = get_assemblyai_api_key()
        if api_key:
            try:
                report("transcribing (cloud)...")
                return assemblyai_engine.transcribe(audio_path, api_key)
            except TranscriptionError:
                logger.warning("AssemblyAI failed for %s, falling back to Whisper", video_info.url)

        # Fall back to Whisper
        report("transcribing (local)...")
        return whisper_engine.transcribe(audio_path, config.whisper_model)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _try_cloud_only(
    video_info: VideoInfo,
    config: Config,
    report: Callable[[str], None],
) -> tuple[Segment, ...]:
    """Transcribe using AssemblyAI only. Requires API key.

    Args:
        video_info: Video metadata.
        config: Application configuration.
        report: Phase status callback.

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
        report("downloading audio...")
        audio_path = download.download_audio(
            video_info.url, Path(temp_dir), config.ffmpeg_location,
        )
        report("transcribing (cloud)...")
        return assemblyai_engine.transcribe(audio_path, api_key)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _try_local_only(
    video_info: VideoInfo,
    config: Config,
    report: Callable[[str], None],
) -> tuple[Segment, ...]:
    """Transcribe using local Whisper only.

    Args:
        video_info: Video metadata.
        config: Application configuration.
        report: Phase status callback.

    Returns:
        Tuple of Segment dataclasses.

    Raises:
        TranscriptionError: If Whisper fails.
    """
    temp_dir = tempfile.mkdtemp(prefix="yt-transcribe-")
    try:
        report("downloading audio...")
        audio_path = download.download_audio(
            video_info.url, Path(temp_dir), config.ffmpeg_location,
        )
        report("transcribing (local)...")
        return whisper_engine.transcribe(audio_path, config.whisper_model)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _format_text(segments: tuple[Segment, ...]) -> str:
    """Format segments into readable text with 5-minute interval timestamps.

    Inserts [MM:SS] markers at every 5-minute boundary. No marker at 00:00.

    Args:
        segments: Tuple of Segment dataclasses to format.

    Returns:
        Formatted transcript text string.
    """
    if not segments:
        return ""

    parts: list[str] = []
    next_timestamp = _TIMESTAMP_INTERVAL

    for segment in segments:
        # Insert timestamp marker if this segment crosses a 5-minute boundary
        while segment.start_seconds >= next_timestamp:
            minutes = int(next_timestamp) // 60
            seconds = int(next_timestamp) % 60
            parts.append(f"\n\n[{minutes:02d}:{seconds:02d}]")
            next_timestamp += _TIMESTAMP_INTERVAL

        parts.append(segment.text)

    return "\n".join(parts)
