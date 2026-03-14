"""Integration tests for CLI commands using click.testing.CliRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from yt_transcribe.models import (
    Config,
    Segment,
    Transcript,
    TranscriptionStrategy,
    VideoInfo,
    WhisperModel,
)


# -- Fixtures ----------------------------------------------------------------

@pytest.fixture()
def runner() -> CliRunner:
    """Return a click test runner."""
    return CliRunner()


@pytest.fixture()
def sample_config(tmp_path: Path) -> Config:
    """Return a Config pointing at a temp vault."""
    return Config(
        obsidian_vault_path=str(tmp_path / "vault"),
        transcript_folder="Transcripts",
        transcription_strategy=TranscriptionStrategy.AUTO,
        whisper_model=WhisperModel.BASE,
        async_threshold_seconds=180,
        parallel_enabled=False,
    )


@pytest.fixture()
def sample_video() -> VideoInfo:
    """Return a minimal VideoInfo."""
    return VideoInfo(
        video_id="abc123abcde",
        title="Test Video",
        channel="Test Channel",
        url="https://youtube.com/watch?v=abc123abcde",
        duration_seconds=120,
        playlist_title=None,
    )


@pytest.fixture()
def sample_transcript(sample_video: VideoInfo) -> Transcript:
    """Return a Transcript for the sample video."""
    return Transcript(
        video=sample_video,
        text="Hello world transcript",
        segments=(Segment(0.0, 5.0, "Hello world transcript"),),
    )


# -- video command -----------------------------------------------------------

class TestVideoCommand:
    """Tests for `yt-transcribe video <url>`."""

    def test_video_success(
        self, runner: CliRunner, sample_config: Config,
        sample_video: VideoInfo, sample_transcript: Transcript,
    ) -> None:
        """Successful transcription prints title and saves."""
        from yt_transcribe.cli import cli
        from yt_transcribe.download import VideoData

        video_data = VideoData(
            video_info=sample_video,
            captions=None,
            audio_url="https://audio.example.com/abc123",
            raw_info={"id": "abc123abcde"},
        )

        with (
            patch("yt_transcribe.cli.load_config", return_value=sample_config),
            patch("yt_transcribe.cli.extract_video_data", return_value=video_data),
            patch("yt_transcribe.cli.storage.find_existing", return_value=None),
            patch(
                "yt_transcribe.cli.transcribe.transcribe_video_fast",
                return_value=sample_transcript,
            ),
            patch("yt_transcribe.cli.storage.save_transcript"),
        ):
            result = runner.invoke(cli, ["video", "https://youtube.com/watch?v=abc123abcde"])

        assert result.exit_code == 0
        assert "Test Video" in result.output

    def test_video_cached(
        self, runner: CliRunner, sample_config: Config, sample_video: VideoInfo,
    ) -> None:
        """Already-cached transcript skips transcription."""
        from yt_transcribe.cli import cli
        from yt_transcribe.download import VideoData

        video_data = VideoData(
            video_info=sample_video,
            captions=None,
            audio_url="https://audio.example.com/abc123",
            raw_info={"id": "abc123abcde"},
        )

        with (
            patch("yt_transcribe.cli.load_config", return_value=sample_config),
            patch("yt_transcribe.cli.extract_video_data", return_value=video_data),
            patch("yt_transcribe.cli.storage.find_existing", return_value=Path("/v/cached.md")),
        ):
            result = runner.invoke(cli, ["video", "https://youtube.com/watch?v=abc123abcde"])

        assert result.exit_code == 0
        assert "already exists" in result.output.lower() or "cached" in result.output.lower()

    def test_video_missing_url(self, runner: CliRunner) -> None:
        """Missing URL argument shows error."""
        from yt_transcribe.cli import cli

        result = runner.invoke(cli, ["video"])
        assert result.exit_code != 0


# -- playlist command --------------------------------------------------------

class TestPlaylistCommand:
    """Tests for `yt-transcribe playlist <url>`."""

    def test_playlist_success(
        self, runner: CliRunner, sample_config: Config,
        sample_video: VideoInfo, sample_transcript: Transcript,
    ) -> None:
        """Playlist processes each video."""
        from yt_transcribe.cli import cli
        from yt_transcribe.download import VideoData

        video_data = VideoData(
            video_info=sample_video,
            captions=None,
            audio_url="https://audio.example.com/abc123",
            raw_info={"id": "abc123abcde"},
        )

        with (
            patch("yt_transcribe.cli.load_config", return_value=sample_config),
            patch("yt_transcribe.cli.download.get_playlist_info", return_value=(sample_video,)),
            patch("yt_transcribe.cli.storage.find_existing", return_value=None),
            patch("yt_transcribe.cli.extract_video_data", return_value=video_data),
            patch(
                "yt_transcribe.cli.transcribe.transcribe_video_fast",
                return_value=sample_transcript,
            ),
            patch("yt_transcribe.cli.storage.save_transcript"),
        ):
            result = runner.invoke(cli, ["playlist", "https://youtube.com/playlist?list=PL1"])

        assert result.exit_code == 0

    def test_playlist_missing_url(self, runner: CliRunner) -> None:
        """Missing URL argument shows error."""
        from yt_transcribe.cli import cli

        result = runner.invoke(cli, ["playlist"])
        assert result.exit_code != 0


# -- list command ------------------------------------------------------------

class TestListCommand:
    """Tests for `yt-transcribe list`."""

    def test_list_shows_transcripts(self, runner: CliRunner, sample_config: Config) -> None:
        """List command shows saved transcript titles."""
        from yt_transcribe.cli import cli
        from yt_transcribe.search import TranscriptEntry

        entries = [
            TranscriptEntry(Path("/v/a.md"), "Video A", "Ch1", "a1"),
        ]
        with (
            patch("yt_transcribe.cli.load_config", return_value=sample_config),
            patch("yt_transcribe.cli.search.list_transcripts", return_value=entries),
        ):
            result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "Video A" in result.output

    def test_list_with_folder(self, runner: CliRunner, sample_config: Config) -> None:
        """Folder flag is forwarded."""
        from yt_transcribe.cli import cli

        with (
            patch("yt_transcribe.cli.load_config", return_value=sample_config),
            patch(
                "yt_transcribe.cli.search.list_transcripts", return_value=[]
            ) as mock_list,
        ):
            result = runner.invoke(cli, ["list", "--folder", "MIT"])

        mock_list.assert_called_once_with(sample_config, folder="MIT")


# -- search command ----------------------------------------------------------

class TestSearchCommand:
    """Tests for `yt-transcribe search <query>`."""

    def test_search_shows_matches(self, runner: CliRunner, sample_config: Config) -> None:
        """Search shows matching snippets."""
        from yt_transcribe.cli import cli
        from yt_transcribe.search import SearchResult

        matches = [
            SearchResult(Path("/v/ml.md"), "ML Intro", "Prof", "...gradient..."),
        ]
        with (
            patch("yt_transcribe.cli.load_config", return_value=sample_config),
            patch("yt_transcribe.cli.search.search_transcripts", return_value=matches),
        ):
            result = runner.invoke(cli, ["search", "gradient"])

        assert result.exit_code == 0
        assert "gradient" in result.output

    def test_search_no_results(self, runner: CliRunner, sample_config: Config) -> None:
        """No matches shows a message."""
        from yt_transcribe.cli import cli

        with (
            patch("yt_transcribe.cli.load_config", return_value=sample_config),
            patch("yt_transcribe.cli.search.search_transcripts", return_value=[]),
        ):
            result = runner.invoke(cli, ["search", "zzzznonexistent"])

        assert result.exit_code == 0
        assert "no" in result.output.lower() or "0" in result.output


# -- jobs command ------------------------------------------------------------

class TestJobsCommand:
    """Tests for `yt-transcribe jobs`."""

    def test_jobs_shows_active(self, runner: CliRunner) -> None:
        """Jobs command shows running and recent jobs."""
        from yt_transcribe.cli import cli

        job_rows = [
            {"job_id": "job-1", "status": "running", "video_count": 5,
             "completed_count": 2, "error": None},
        ]
        mock_conn = MagicMock()
        with (
            patch("yt_transcribe.cli._get_db", return_value=mock_conn),
            patch("yt_transcribe.cli.jobs.list_jobs", return_value=job_rows),
        ):
            result = runner.invoke(cli, ["jobs"])

        assert result.exit_code == 0
        assert "job-1" in result.output


# -- config command ----------------------------------------------------------

class TestConfigCommand:
    """Tests for `yt-transcribe config` and `config set`."""

    def test_config_shows_values(self, runner: CliRunner, sample_config: Config) -> None:
        """Config command prints current settings."""
        from yt_transcribe.cli import cli

        with patch("yt_transcribe.cli.load_config", return_value=sample_config):
            result = runner.invoke(cli, ["config"])

        assert result.exit_code == 0
        assert "auto" in result.output.lower()

    def test_config_set_updates_value(self, runner: CliRunner, sample_config: Config) -> None:
        """Config set writes new value."""
        from yt_transcribe.cli import cli

        with (
            patch("yt_transcribe.cli.load_config", return_value=sample_config),
            patch("yt_transcribe.cli.config_mod.save_config") as mock_save,
        ):
            result = runner.invoke(cli, ["config", "set", "whisper_model", "small"])

        assert result.exit_code == 0
        mock_save.assert_called_once()

    def test_config_set_invalid_key(self, runner: CliRunner, sample_config: Config) -> None:
        """Unknown config key shows error."""
        from yt_transcribe.cli import cli

        with patch("yt_transcribe.cli.load_config", return_value=sample_config):
            result = runner.invoke(cli, ["config", "set", "bogus_key", "value"])

        assert result.exit_code != 0 or "unknown" in result.output.lower()
