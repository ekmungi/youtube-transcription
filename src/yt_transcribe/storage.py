"""Markdown storage for Obsidian vault -- write and deduplicate transcripts."""

from __future__ import annotations

import re
from pathlib import Path

from yt_transcribe.models import Config, Transcript


def sanitize_filename(name: str) -> str:
    """Remove filesystem-unsafe characters and normalize whitespace.

    Args:
        name: Raw video title.

    Returns:
        Cleaned string safe for use as a filename (without extension).
    """
    # Replace backslashes, pipes, and forward slashes with underscores
    cleaned = re.sub(r'[\\|/]', '_', name)
    # Remove other unsafe characters
    cleaned = re.sub(r'[<>:?"*]', '', cleaned)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Truncate to 200 characters
    cleaned = cleaned[:200]
    return cleaned if cleaned else "untitled"


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS or H:MM:SS string.

    Args:
        seconds: Total duration in seconds.

    Returns:
        Human-readable duration string.
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _format_timestamp(seconds: float) -> str:
    """Format a timestamp in seconds to [MM:SS] bracket notation.

    Args:
        seconds: Timestamp in seconds.

    Returns:
        Formatted timestamp string like [05:00].
    """
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    return f"[{minutes:02d}:{secs:02d}]"


def _build_body_with_timestamps(transcript: Transcript) -> str:
    """Build transcript body text with timestamps at 5-minute intervals.

    Inserts timestamp markers at every 5-minute boundary based on
    segment start times.

    Args:
        transcript: Complete transcript with segments.

    Returns:
        Formatted body text with timestamp markers.
    """
    if not transcript.segments:
        return transcript.text

    lines: list[str] = []
    next_marker = 300  # first marker at 5 minutes (300 seconds)

    for segment in transcript.segments:
        # Insert timestamp marker when segment crosses a 5-minute boundary
        while segment.start_seconds >= next_marker:
            lines.append("")
            lines.append(_format_timestamp(next_marker))
            next_marker += 300

        lines.append(segment.text)

    return "\n".join(lines)


def format_markdown(transcript: Transcript) -> str:
    """Format a transcript as a complete markdown document with frontmatter.

    Includes YAML frontmatter (title, channel, url, video_id, date, duration,
    tags) and body text with timestamps at 5-minute intervals.

    Args:
        transcript: Complete transcript to format.

    Returns:
        Full markdown string ready to write to disk.
    """
    from datetime import date

    video = transcript.video
    duration_str = _format_duration(video.duration_seconds)
    today = date.today().isoformat()

    frontmatter = (
        "---\n"
        f'title: "{video.title}"\n'
        f'channel: "{video.channel}"\n'
        f"url: \"{video.url}\"\n"
        f'video_id: "{video.video_id}"\n'
        f"date: {today}\n"
        f'duration: "{duration_str}"\n'
        "tags:\n"
        "  - youtube\n"
        "  - transcript\n"
        "---\n"
    )

    body = _build_body_with_timestamps(transcript)

    return f"{frontmatter}\n# {video.title}\n\n{body}\n"


def _transcript_folder_path(config: Config) -> Path:
    """Resolve the full path to the transcript folder in the vault.

    Args:
        config: Application configuration.

    Returns:
        Absolute path to the transcript output folder.
    """
    return Path(config.obsidian_vault_path) / config.transcript_folder


def find_existing(config: Config, video_id: str) -> Path | None:
    """Search for an existing transcript markdown file by video_id.

    Scans all .md files in the transcript folder and checks frontmatter
    for a matching video_id field.

    Args:
        config: Application configuration.
        video_id: YouTube video ID to search for.

    Returns:
        Path to existing file if found, None otherwise.
    """
    folder = _transcript_folder_path(config)
    if not folder.exists():
        return None

    target = f'video_id: "{video_id}"'
    for md_file in folder.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if target in content:
            return md_file

    return None


def save_transcript(config: Config, transcript: Transcript) -> Path:
    """Save a transcript as a markdown file to the Obsidian vault.

    Single videos go to {vault}/{folder}/{title}.md.
    Playlist videos go to {vault}/{folder}/{playlist_name}/{title}.md.
    Deduplicates by video_id -- returns existing path if already saved.

    Args:
        config: Application configuration.
        transcript: Complete transcript to save.

    Returns:
        Path to the saved (or existing) markdown file.
    """
    # Deduplication check
    existing = find_existing(config, transcript.video.video_id)
    if existing is not None:
        return existing

    folder = _transcript_folder_path(config)

    # Playlist videos get a subfolder
    if transcript.video.playlist_title is not None:
        folder = folder / sanitize_filename(transcript.video.playlist_title)

    folder.mkdir(parents=True, exist_ok=True)

    filename = sanitize_filename(transcript.video.title) + ".md"
    file_path = folder / filename

    markdown = format_markdown(transcript)
    file_path.write_text(markdown, encoding="utf-8")

    return file_path
