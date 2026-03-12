"""YouTube download module using yt-dlp Python API for metadata, captions, and audio."""

from __future__ import annotations

import logging
from pathlib import Path

import yt_dlp
from tenacity import retry, stop_after_attempt, wait_exponential

from yt_transcribe.exceptions import (
    DownloadError,
    PlaylistNotFoundError,
    VideoNotFoundError,
    VideoUnavailableError,
)
from yt_transcribe.models import Segment, VideoInfo

logger = logging.getLogger(__name__)

# Strings in yt-dlp errors that indicate a private/unavailable video
_UNAVAILABLE_PATTERNS = ("private video", "age-restricted", "not available", "sign in")


def _is_unavailable_error(error_msg: str) -> bool:
    """Check if the error message indicates a private or unavailable video."""
    lower = error_msg.lower()
    return any(pattern in lower for pattern in _UNAVAILABLE_PATTERNS)


def _build_video_info(info: dict, playlist_title: str | None = None) -> VideoInfo:
    """Build an immutable VideoInfo from a yt-dlp info dict.

    Args:
        info: yt-dlp extracted info dictionary.
        playlist_title: Title of the parent playlist, or None for standalone videos.

    Returns:
        A frozen VideoInfo dataclass instance.
    """
    return VideoInfo(
        video_id=info["id"],
        title=info.get("title", "Untitled"),
        channel=info.get("channel", info.get("uploader", "Unknown")),
        url=info.get("webpage_url", info.get("url", "")),
        duration_seconds=int(info.get("duration", 0)),
        playlist_title=playlist_title,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_video_info(url: str) -> VideoInfo:
    """Fetch video metadata from YouTube.

    Args:
        url: YouTube video URL.

    Returns:
        Immutable VideoInfo with video metadata.

    Raises:
        VideoNotFoundError: Video does not exist or URL is invalid.
        VideoUnavailableError: Video is private, age-restricted, or region-blocked.
    """
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        msg = str(exc)
        if _is_unavailable_error(msg):
            raise VideoUnavailableError(msg) from exc
        raise VideoNotFoundError(msg) from exc

    if info is None:
        raise VideoNotFoundError(f"No info returned for URL: {url}")

    return _build_video_info(info)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_playlist_info(url: str) -> tuple[VideoInfo, ...]:
    """Expand a playlist URL into a tuple of VideoInfo objects.

    Args:
        url: YouTube playlist URL.

    Returns:
        Tuple of VideoInfo, one per video in the playlist.

    Raises:
        PlaylistNotFoundError: Playlist does not exist or is empty.
    """
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": False}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise PlaylistNotFoundError(str(exc)) from exc

    if info is None:
        raise PlaylistNotFoundError(f"No info returned for playlist: {url}")

    entries = info.get("entries", [])
    # Filter out None entries (unavailable videos in playlist)
    valid_entries = [e for e in entries if e is not None]

    if not valid_entries:
        raise PlaylistNotFoundError(f"Playlist is empty: {url}")

    playlist_title = info.get("title", "Unknown Playlist")
    return tuple(_build_video_info(entry, playlist_title) for entry in valid_entries)


def get_captions(url: str) -> tuple[Segment, ...] | None:
    """Extract existing captions/subtitles from a YouTube video.

    Args:
        url: YouTube video URL.

    Returns:
        Tuple of Segments if captions exist, None otherwise.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "json3",
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return None

    if info is None:
        return None

    requested_subs = info.get("requested_subtitles")
    if not requested_subs:
        return None

    # Try English subtitles first
    sub_info = requested_subs.get("en")
    if sub_info is None:
        return None

    sub_data = sub_info.get("data")
    if not sub_data:
        return None

    return _parse_subtitle_data(sub_data)


def _parse_subtitle_data(sub_data: list[dict]) -> tuple[Segment, ...]:
    """Parse subtitle data entries into immutable Segment tuples.

    Args:
        sub_data: List of subtitle entry dicts with start, duration, and text keys.

    Returns:
        Tuple of Segment dataclass instances.
    """
    segments = []
    for entry in sub_data:
        start = float(entry.get("start", 0.0))
        duration = float(entry.get("duration", 0.0))
        text = entry.get("text", "").strip()
        if text:
            segments.append(Segment(
                start_seconds=start,
                end_seconds=start + duration,
                text=text,
            ))
    return tuple(segments)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def download_audio(url: str, output_dir: Path) -> Path:
    """Download audio from a YouTube video to a local directory.

    Args:
        url: YouTube video URL.
        output_dir: Directory to save the audio file.

    Returns:
        Path to the downloaded audio file.

    Raises:
        DownloadError: Network or extraction failure during download.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
        }],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise DownloadError(f"No info returned during download: {url}")
            filename = ydl.prepare_filename(info)
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(str(exc)) from exc

    return Path(filename)
