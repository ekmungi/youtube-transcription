"""Integration tests for MCP server tools. Core functions are mocked."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yt_transcribe.models import (
    Config,
    JobStatus,
    Segment,
    Transcript,
    TranscriptionStrategy,
    VideoInfo,
    WhisperModel,
)


# -- Fixtures ----------------------------------------------------------------

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
        video_id="abc123",
        title="Test Video",
        channel="Test Channel",
        url="https://youtube.com/watch?v=abc123",
        duration_seconds=120,
        playlist_title=None,
    )


@pytest.fixture()
def sample_transcript(sample_video: VideoInfo) -> Transcript:
    """Return a Transcript for the sample video."""
    return Transcript(
        video=sample_video,
        text="Hello world",
        segments=(Segment(0.0, 5.0, "Hello world"),),
    )


# -- get_transcript ----------------------------------------------------------

class TestGetTranscript:
    """Tests for the get_transcript MCP tool handler."""

    @pytest.mark.asyncio()
    async def test_returns_cached_transcript(
        self, sample_config: Config, tmp_path: Path
    ) -> None:
        """Cache hit returns path without transcribing."""
        from yt_transcribe.mcp_server import handle_get_transcript

        cache_path = tmp_path / "vault" / "Transcripts" / "cached.md"
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text("cached", encoding="utf-8")

        with (
            patch("yt_transcribe.mcp_server.load_config", return_value=sample_config),
            patch("yt_transcribe.mcp_server.storage.find_existing", return_value=cache_path),
        ):
            result = await handle_get_transcript("https://youtube.com/watch?v=abc123abcde")

        assert result["source"] == "cache"

    @pytest.mark.asyncio()
    async def test_sync_transcription_for_short_video(
        self,
        sample_config: Config,
        sample_video: VideoInfo,
        sample_transcript: Transcript,
    ) -> None:
        """Short video is transcribed synchronously and returned inline."""
        from yt_transcribe.download import VideoData
        from yt_transcribe.mcp_server import handle_get_transcript

        video_data = VideoData(
            video_info=sample_video,
            captions=None,
            audio_url="https://audio.example.com/abc123",
            raw_info={"id": "abc123"},
        )

        with (
            patch("yt_transcribe.mcp_server.load_config", return_value=sample_config),
            patch("yt_transcribe.mcp_server.storage.find_existing", return_value=None),
            patch("yt_transcribe.mcp_server.extract_video_data", return_value=video_data),
            patch(
                "yt_transcribe.mcp_server.transcribe.transcribe_video_fast",
                return_value=sample_transcript,
            ),
            patch("yt_transcribe.mcp_server.storage.save_transcript") as mock_save,
        ):
            result = await handle_get_transcript("https://youtube.com/watch?v=abc123")

        assert result["text"] == "Hello world"
        assert result["source"] == "transcribed"
        mock_save.assert_called_once()

    @pytest.mark.asyncio()
    async def test_async_job_for_long_video(self, sample_config: Config) -> None:
        """Long video exceeding threshold returns a job_id."""
        from yt_transcribe.download import VideoData
        from yt_transcribe.mcp_server import handle_get_transcript

        long_video = VideoInfo(
            video_id="long1",
            title="Long Video",
            channel="C",
            url="https://youtube.com/watch?v=long1",
            duration_seconds=7200,
            playlist_title=None,
        )
        video_data = VideoData(
            video_info=long_video,
            captions=None,
            audio_url="https://audio.example.com/long1",
            raw_info={"id": "long1"},
        )
        mock_conn = MagicMock()
        with (
            patch("yt_transcribe.mcp_server.load_config", return_value=sample_config),
            patch("yt_transcribe.mcp_server.storage.find_existing", return_value=None),
            patch("yt_transcribe.mcp_server.extract_video_data", return_value=video_data),
            patch("yt_transcribe.mcp_server._get_db", return_value=mock_conn),
            patch("yt_transcribe.mcp_server.jobs.create_job", return_value="job-001"),
        ):
            result = await handle_get_transcript("https://youtube.com/watch?v=long1")

        assert result["job_id"] == "job-001"
        assert "async" in result["status"]


# -- get_playlist_transcripts ------------------------------------------------

class TestGetPlaylistTranscripts:
    """Tests for the get_playlist_transcripts MCP tool handler."""

    @pytest.mark.asyncio()
    async def test_short_playlist_sync(
        self,
        sample_config: Config,
        sample_video: VideoInfo,
        sample_transcript: Transcript,
    ) -> None:
        """Playlist with short total duration is processed synchronously."""
        from yt_transcribe.download import VideoData
        from yt_transcribe.mcp_server import handle_get_playlist_transcripts

        video_data = VideoData(
            video_info=sample_video,
            captions=None,
            audio_url="https://audio.example.com/abc123",
            raw_info={"id": "abc123"},
        )

        with (
            patch("yt_transcribe.mcp_server.load_config", return_value=sample_config),
            patch(
                "yt_transcribe.mcp_server.download.get_playlist_info",
                return_value=(sample_video,),
            ),
            patch("yt_transcribe.mcp_server.storage.find_existing", return_value=None),
            patch("yt_transcribe.mcp_server.extract_video_data", return_value=video_data),
            patch(
                "yt_transcribe.mcp_server.transcribe.transcribe_video_fast",
                return_value=sample_transcript,
            ),
            patch("yt_transcribe.mcp_server.storage.save_transcript"),
        ):
            result = await handle_get_playlist_transcripts(
                "https://youtube.com/playlist?list=PL123"
            )

        assert len(result["transcripts"]) == 1

    @pytest.mark.asyncio()
    async def test_long_playlist_async(self, sample_config: Config) -> None:
        """Playlist exceeding threshold returns job_id."""
        from yt_transcribe.mcp_server import handle_get_playlist_transcripts

        videos = tuple(
            VideoInfo(
                video_id=f"v{i}",
                title=f"Lecture {i}",
                channel="C",
                url=f"https://youtube.com/watch?v=v{i}",
                duration_seconds=3600,
                playlist_title="Big Course",
            )
            for i in range(5)
        )
        mock_conn = MagicMock()
        with (
            patch("yt_transcribe.mcp_server.load_config", return_value=sample_config),
            patch("yt_transcribe.mcp_server.download.get_playlist_info", return_value=videos),
            patch("yt_transcribe.mcp_server._get_db", return_value=mock_conn),
            patch("yt_transcribe.mcp_server.jobs.create_job", return_value="job-002"),
        ):
            result = await handle_get_playlist_transcripts(
                "https://youtube.com/playlist?list=PL999"
            )

        assert result["job_id"] == "job-002"


# -- list_transcripts --------------------------------------------------------

class TestListTranscripts:
    """Tests for the list_transcripts MCP tool handler."""

    @pytest.mark.asyncio()
    async def test_list_returns_entries(self, sample_config: Config) -> None:
        """List returns metadata for saved transcripts."""
        from yt_transcribe.mcp_server import handle_list_transcripts
        from yt_transcribe.search import TranscriptEntry

        entries = [
            TranscriptEntry(Path("/vault/a.md"), "Video A", "Ch1", "a1"),
            TranscriptEntry(Path("/vault/b.md"), "Video B", "Ch2", "b2"),
        ]
        with (
            patch("yt_transcribe.mcp_server.load_config", return_value=sample_config),
            patch("yt_transcribe.mcp_server.search.list_transcripts", return_value=entries),
        ):
            result = await handle_list_transcripts(folder=None)

        assert len(result["transcripts"]) == 2
        assert result["transcripts"][0]["title"] == "Video A"

    @pytest.mark.asyncio()
    async def test_list_with_folder_filter(self, sample_config: Config) -> None:
        """Folder argument is forwarded to list function."""
        from yt_transcribe.mcp_server import handle_list_transcripts

        with (
            patch("yt_transcribe.mcp_server.load_config", return_value=sample_config),
            patch(
                "yt_transcribe.mcp_server.search.list_transcripts", return_value=[]
            ) as mock_list,
        ):
            await handle_list_transcripts(folder="MIT Course")

        mock_list.assert_called_once_with(sample_config, folder="MIT Course")


# -- search_transcripts ------------------------------------------------------

class TestSearchTranscripts:
    """Tests for the search_transcripts MCP tool handler."""

    @pytest.mark.asyncio()
    async def test_search_returns_matches(self, sample_config: Config) -> None:
        """Search returns matching snippets."""
        from yt_transcribe.mcp_server import handle_search_transcripts
        from yt_transcribe.search import SearchResult

        matches = [
            SearchResult(Path("/vault/ml.md"), "ML Intro", "Prof", "...gradient descent..."),
        ]
        with (
            patch("yt_transcribe.mcp_server.load_config", return_value=sample_config),
            patch("yt_transcribe.mcp_server.search.search_transcripts", return_value=matches),
        ):
            result = await handle_search_transcripts("gradient descent")

        assert len(result["matches"]) == 1
        assert "gradient" in result["matches"][0]["snippet"]

    @pytest.mark.asyncio()
    async def test_search_empty_results(self, sample_config: Config) -> None:
        """No matches returns empty list."""
        from yt_transcribe.mcp_server import handle_search_transcripts

        with (
            patch("yt_transcribe.mcp_server.load_config", return_value=sample_config),
            patch("yt_transcribe.mcp_server.search.search_transcripts", return_value=[]),
        ):
            result = await handle_search_transcripts("nonexistent term xyz")

        assert result["matches"] == []


# -- check_job_status --------------------------------------------------------

class TestCheckJobStatus:
    """Tests for the check_job_status MCP tool handler."""

    @pytest.mark.asyncio()
    async def test_returns_job_state(self) -> None:
        """Returns current job status and progress."""
        from yt_transcribe.mcp_server import handle_check_job_status

        job_row = {
            "job_id": "job-001",
            "status": "running",
            "video_count": 5,
            "completed_count": 3,
            "error": None,
        }
        mock_conn = MagicMock()
        with (
            patch("yt_transcribe.mcp_server._get_db", return_value=mock_conn),
            patch("yt_transcribe.mcp_server.jobs.get_job", return_value=job_row),
        ):
            result = await handle_check_job_status("job-001")

        assert result["status"] == "running"
        assert result["completed_count"] == 3

    @pytest.mark.asyncio()
    async def test_unknown_job_returns_error(self) -> None:
        """Unknown job_id returns error response."""
        from yt_transcribe.mcp_server import handle_check_job_status

        mock_conn = MagicMock()
        with (
            patch("yt_transcribe.mcp_server._get_db", return_value=mock_conn),
            patch("yt_transcribe.mcp_server.jobs.get_job", return_value=None),
        ):
            result = await handle_check_job_status("bogus-id")

        assert result["error"] is not None
