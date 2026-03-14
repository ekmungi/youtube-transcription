"""Tests for markdown storage to Obsidian vault."""

from pathlib import Path

import pytest

from yt_transcribe.models import (
    Config,
    Segment,
    Transcript,
    TranscriptionStrategy,
    VideoInfo,
    WhisperModel,
)
from yt_transcribe.storage import (
    _build_filename,
    find_existing,
    format_markdown,
    sanitize_filename,
    save_transcript,
)


def _make_config(tmp_path: Path) -> Config:
    """Build a Config pointing at a temporary vault directory."""
    return Config(
        obsidian_vault_path=str(tmp_path / "vault"),
        transcript_folder="Sources/YouTube Transcripts",
        transcription_strategy=TranscriptionStrategy.AUTO,
        whisper_model=WhisperModel.BASE,
        async_threshold_seconds=180,
        parallel_enabled=False,
    )


def _make_video(
    video_id: str = "abc123",
    title: str = "Test Video",
    channel: str = "Test Channel",
    duration: int = 600,
    playlist_title: str | None = None,
) -> VideoInfo:
    """Build a VideoInfo with sensible defaults."""
    return VideoInfo(
        video_id=video_id,
        title=title,
        channel=channel,
        url=f"https://youtube.com/watch?v={video_id}",
        duration_seconds=duration,
        playlist_title=playlist_title,
    )


def _make_transcript(
    video: VideoInfo | None = None,
    text: str = "Hello world",
    segments: tuple[Segment, ...] | None = None,
) -> Transcript:
    """Build a Transcript with sensible defaults."""
    if video is None:
        video = _make_video()
    if segments is None:
        segments = (Segment(start_seconds=0.0, end_seconds=5.0, text="Hello world"),)
    return Transcript(video=video, text=text, segments=segments)


class TestSanitizeFilename:
    def test_removes_special_characters(self):
        assert sanitize_filename('What is AI? A Guide: Part 1/2') == "What is AI A Guide Part 1_2"

    def test_strips_leading_trailing_whitespace(self):
        assert sanitize_filename("  spaces  ") == "spaces"

    def test_collapses_multiple_spaces(self):
        assert sanitize_filename("a   b") == "a b"

    def test_replaces_backslash_and_pipe(self):
        assert sanitize_filename(r"foo\bar|baz") == "foo_bar_baz"

    def test_empty_string_returns_untitled(self):
        assert sanitize_filename("") == "untitled"

    def test_truncates_long_names(self):
        long_name = "A" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200


class TestFormatMarkdown:
    def test_frontmatter_fields(self):
        transcript = _make_transcript()
        md = format_markdown(transcript)
        assert "---" in md
        assert 'title: "Test Video"' in md
        assert 'channel: "Test Channel"' in md
        assert 'video_id: "abc123"' in md
        assert "url: " in md
        assert "duration: " in md
        assert "- youtube" in md
        assert "- transcript" in md

    def test_heading_matches_title(self):
        transcript = _make_transcript()
        md = format_markdown(transcript)
        assert "# Test Video" in md

    def test_body_contains_text(self):
        segments = (Segment(start_seconds=0.0, end_seconds=5.0, text="Some transcript content here"),)
        transcript = _make_transcript(text="Some transcript content here", segments=segments)
        md = format_markdown(transcript)
        assert "Some transcript content here" in md

    def test_timestamps_at_five_minute_intervals(self):
        segments = (
            Segment(0.0, 60.0, "Intro text."),
            Segment(60.0, 300.0, "More content here."),
            Segment(300.0, 600.0, "After five minutes."),
            Segment(600.0, 900.0, "Ten minute mark."),
        )
        video = _make_video(duration=900)
        transcript = _make_transcript(
            video=video,
            text="Intro text. More content here. After five minutes. Ten minute mark.",
            segments=segments,
        )
        md = format_markdown(transcript)
        assert "[05:00]" in md
        assert "[10:00]" in md

    def test_duration_formatted_as_mmss(self):
        video = _make_video(duration=2732)  # 45:32
        transcript = _make_transcript(video=video)
        md = format_markdown(transcript)
        assert 'duration: "45:32"' in md

    def test_duration_formatted_as_hmmss_for_long_videos(self):
        video = _make_video(duration=7384)  # 2:03:04
        transcript = _make_transcript(video=video)
        md = format_markdown(transcript)
        assert 'duration: "2:03:04"' in md


class TestBuildFilename:
    """Tests for the _build_filename helper."""

    def test_includes_video_id_in_brackets(self):
        """Filename includes [video_id] for fast glob lookup."""
        result = _build_filename("Test Video", "abc123")
        assert result == "Test Video [abc123].md"

    def test_sanitizes_title(self):
        """Title is sanitized in the filename."""
        result = _build_filename("What is AI? Part 1/2", "xyz789")
        assert "?" not in result
        assert "[xyz789].md" in result


class TestSaveTranscript:
    def test_creates_markdown_file(self, tmp_path: Path):
        config = _make_config(tmp_path)
        transcript = _make_transcript()
        result = save_transcript(config, transcript)
        assert result.exists()
        assert result.suffix == ".md"
        assert result.read_text().startswith("---")

    def test_single_video_path(self, tmp_path: Path):
        config = _make_config(tmp_path)
        transcript = _make_transcript()
        result = save_transcript(config, transcript)
        expected_dir = Path(config.obsidian_vault_path) / config.transcript_folder
        assert result.parent == expected_dir

    def test_filename_includes_video_id(self, tmp_path: Path):
        """Saved filename includes [video_id] for fast lookup."""
        config = _make_config(tmp_path)
        transcript = _make_transcript()
        result = save_transcript(config, transcript)
        assert "[abc123]" in result.name

    def test_playlist_video_in_subfolder(self, tmp_path: Path):
        config = _make_config(tmp_path)
        video = _make_video(playlist_title="MIT 6.034")
        transcript = _make_transcript(video=video)
        result = save_transcript(config, transcript)
        expected_dir = (
            Path(config.obsidian_vault_path) / config.transcript_folder / "MIT 6.034"
        )
        assert result.parent == expected_dir

    def test_filename_is_sanitized_title(self, tmp_path: Path):
        config = _make_config(tmp_path)
        video = _make_video(title="What is AI? Part 1/2")
        transcript = _make_transcript(video=video)
        result = save_transcript(config, transcript)
        assert "?" not in result.name
        assert "/" not in result.name

    def test_creates_parent_directories(self, tmp_path: Path):
        config = _make_config(tmp_path)
        transcript = _make_transcript()
        result = save_transcript(config, transcript)
        assert result.parent.is_dir()


class TestFindExisting:
    def test_finds_existing_by_video_id(self, tmp_path: Path):
        config = _make_config(tmp_path)
        transcript = _make_transcript()
        saved_path = save_transcript(config, transcript)
        found = find_existing(config, "abc123")
        assert found == saved_path

    def test_returns_none_when_not_found(self, tmp_path: Path):
        config = _make_config(tmp_path)
        found = find_existing(config, "nonexistent")
        assert found is None

    def test_deduplication_skips_save(self, tmp_path: Path):
        config = _make_config(tmp_path)
        transcript = _make_transcript()
        first = save_transcript(config, transcript)
        second = save_transcript(config, transcript)
        assert first == second
        # Verify only one file with this video_id exists
        folder = Path(config.obsidian_vault_path) / config.transcript_folder
        md_files = list(folder.glob("*.md"))
        assert len(md_files) == 1

    def test_finds_legacy_file_without_video_id_in_name(self, tmp_path: Path):
        """Falls back to frontmatter scan for files without [video_id] in name."""
        config = _make_config(tmp_path)
        folder = Path(config.obsidian_vault_path) / config.transcript_folder
        folder.mkdir(parents=True)
        # Write a legacy-format file (no video_id in filename)
        legacy_file = folder / "Old Video.md"
        legacy_file.write_text(
            '---\nvideo_id: "legacy123"\n---\nContent here\n',
            encoding="utf-8",
        )

        found = find_existing(config, "legacy123")
        assert found == legacy_file
