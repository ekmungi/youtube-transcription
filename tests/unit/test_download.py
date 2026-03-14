"""Tests for YouTube download module. All yt-dlp calls are mocked."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yt_transcribe.download import (
    VideoData,
    _extract_audio_url,
    _extract_captions_from_info,
    download_audio,
    extract_video_data,
    get_captions,
    get_playlist_info,
    get_video_info,
)
from yt_transcribe.exceptions import (
    DownloadError,
    PlaylistNotFoundError,
    VideoNotFoundError,
    VideoUnavailableError,
)
from yt_transcribe.models import Segment, VideoInfo


# -- Fixtures --

SAMPLE_INFO_DICT = {
    "id": "abc123",
    "title": "Test Video",
    "channel": "Test Channel",
    "webpage_url": "https://www.youtube.com/watch?v=abc123",
    "duration": 600,
}

SAMPLE_PLAYLIST_DICT = {
    "id": "PLabc",
    "title": "Test Playlist",
    "entries": [
        {
            "id": "vid1",
            "title": "Video 1",
            "channel": "Ch",
            "webpage_url": "https://www.youtube.com/watch?v=vid1",
            "duration": 300,
        },
        {
            "id": "vid2",
            "title": "Video 2",
            "channel": "Ch",
            "webpage_url": "https://www.youtube.com/watch?v=vid2",
            "duration": 450,
        },
    ],
}


# -- get_video_info tests --

class TestGetVideoInfo:
    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_returns_video_info(self, mock_ydl_cls: MagicMock):
        """get_video_info returns a VideoInfo from yt-dlp metadata."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = SAMPLE_INFO_DICT

        result = get_video_info("https://www.youtube.com/watch?v=abc123")

        assert isinstance(result, VideoInfo)
        assert result.video_id == "abc123"
        assert result.title == "Test Video"
        assert result.channel == "Test Channel"
        assert result.duration_seconds == 600
        assert result.playlist_title is None

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_raises_video_not_found(self, mock_ydl_cls: MagicMock):
        """get_video_info raises VideoNotFoundError for missing videos."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Video unavailable")

        with pytest.raises(VideoNotFoundError):
            get_video_info("https://www.youtube.com/watch?v=missing")

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_raises_video_unavailable_for_private(self, mock_ydl_cls: MagicMock):
        """get_video_info raises VideoUnavailableError for private videos."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Private video")

        with pytest.raises(VideoUnavailableError):
            get_video_info("https://www.youtube.com/watch?v=private")


# -- get_playlist_info tests --

class TestGetPlaylistInfo:
    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_returns_tuple_of_video_info(self, mock_ydl_cls: MagicMock):
        """get_playlist_info returns a tuple of VideoInfo objects."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = SAMPLE_PLAYLIST_DICT

        result = get_playlist_info("https://www.youtube.com/playlist?list=PLabc")

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0].video_id == "vid1"
        assert result[0].playlist_title == "Test Playlist"
        assert result[1].video_id == "vid2"

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_raises_playlist_not_found_on_empty(self, mock_ydl_cls: MagicMock):
        """get_playlist_info raises PlaylistNotFoundError for empty playlists."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {"id": "PL1", "title": "Empty", "entries": []}

        with pytest.raises(PlaylistNotFoundError):
            get_playlist_info("https://www.youtube.com/playlist?list=PL1")

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_raises_playlist_not_found_on_error(self, mock_ydl_cls: MagicMock):
        """get_playlist_info raises PlaylistNotFoundError on extraction failure."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Playlist not found")

        with pytest.raises(PlaylistNotFoundError):
            get_playlist_info("https://www.youtube.com/playlist?list=bad")


# -- get_captions tests --

class TestGetCaptions:
    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_returns_segments_when_captions_exist(self, mock_ydl_cls: MagicMock):
        """get_captions returns tuple of Segments from subtitle data."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        info_with_subs = {
            **SAMPLE_INFO_DICT,
            "subtitles": {"en": [{"ext": "json3", "url": "https://example.com/subs"}]},
            "requested_subtitles": {
                "en": {
                    "ext": "json3",
                    "data": [
                        {"start": 0.0, "duration": 5.0, "text": "Hello world"},
                        {"start": 5.0, "duration": 3.0, "text": "Second line"},
                    ],
                }
            },
        }
        mock_ydl.extract_info.return_value = info_with_subs

        result = get_captions("https://www.youtube.com/watch?v=abc123")

        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Segment)
        assert result[0].text == "Hello world"

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_returns_none_when_no_captions(self, mock_ydl_cls: MagicMock):
        """get_captions returns None when video has no subtitles."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {
            **SAMPLE_INFO_DICT,
            "subtitles": {},
            "requested_subtitles": None,
        }

        result = get_captions("https://www.youtube.com/watch?v=abc123")

        assert result is None


# -- download_audio tests --

class TestDownloadAudio:
    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_returns_path_to_audio_file(self, mock_ydl_cls: MagicMock, tmp_path: Path):
        """download_audio returns a Path to the downloaded audio."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Simulate yt-dlp writing a file
        audio_file = tmp_path / "audio.m4a"
        audio_file.write_bytes(b"fake audio data")
        mock_ydl.extract_info.return_value = {**SAMPLE_INFO_DICT}
        mock_ydl.prepare_filename.return_value = str(audio_file)

        result = download_audio("https://www.youtube.com/watch?v=abc123", tmp_path)

        assert isinstance(result, Path)

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_raises_download_error_on_failure(self, mock_ydl_cls: MagicMock, tmp_path: Path):
        """download_audio raises DownloadError on network failure."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Network error")

        with pytest.raises(DownloadError):
            download_audio("https://www.youtube.com/watch?v=abc123", tmp_path)


# -- extract_video_data tests (single-call optimization) --

SAMPLE_INFO_WITH_SUBS = {
    **SAMPLE_INFO_DICT,
    "formats": [
        {"format_id": "251", "acodec": "opus", "vcodec": "none", "abr": 128, "url": "https://audio.example.com/251"},
        {"format_id": "140", "acodec": "mp4a", "vcodec": "none", "abr": 96, "url": "https://audio.example.com/140"},
    ],
    "requested_subtitles": {
        "en": {
            "ext": "json3",
            "data": [
                {"start": 0.0, "duration": 5.0, "text": "Hello world"},
                {"start": 5.0, "duration": 3.0, "text": "Second line"},
            ],
        }
    },
}


class TestExtractVideoData:
    """Tests for the single-call extract_video_data function."""

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_returns_video_data_with_all_fields(self, mock_ydl_cls: MagicMock):
        """extract_video_data returns VideoData with metadata, captions, and audio URL."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = SAMPLE_INFO_WITH_SUBS

        result = extract_video_data("https://www.youtube.com/watch?v=abc123")

        assert isinstance(result, VideoData)
        assert result.video_info.video_id == "abc123"
        assert result.captions is not None
        assert len(result.captions) == 2
        assert result.audio_url == "https://audio.example.com/251"  # highest abr

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_returns_none_captions_when_no_subs(self, mock_ydl_cls: MagicMock):
        """extract_video_data returns None captions when video has no subtitles."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        info_no_subs = {**SAMPLE_INFO_DICT, "requested_subtitles": None, "formats": []}
        mock_ydl.extract_info.return_value = info_no_subs

        result = extract_video_data("https://www.youtube.com/watch?v=abc123")

        assert result.captions is None

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_raises_video_not_found(self, mock_ydl_cls: MagicMock):
        """extract_video_data raises VideoNotFoundError on missing video."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Video not found")

        with pytest.raises(VideoNotFoundError):
            extract_video_data("https://www.youtube.com/watch?v=missing")

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_raises_video_unavailable_for_private(self, mock_ydl_cls: MagicMock):
        """extract_video_data raises VideoUnavailableError for private videos."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Private video")

        with pytest.raises(VideoUnavailableError):
            extract_video_data("https://www.youtube.com/watch?v=private")

    @patch("yt_transcribe.download.yt_dlp.YoutubeDL")
    def test_single_extract_info_call(self, mock_ydl_cls: MagicMock):
        """extract_video_data makes exactly one extract_info call."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = SAMPLE_INFO_WITH_SUBS

        extract_video_data("https://www.youtube.com/watch?v=abc123")

        mock_ydl.extract_info.assert_called_once()


class TestExtractAudioUrl:
    """Tests for _extract_audio_url helper."""

    def test_picks_highest_bitrate_audio(self):
        """Selects audio format with highest abr."""
        info = {
            "formats": [
                {"acodec": "opus", "vcodec": "none", "abr": 64, "url": "https://low.com"},
                {"acodec": "opus", "vcodec": "none", "abr": 128, "url": "https://high.com"},
            ]
        }
        assert _extract_audio_url(info) == "https://high.com"

    def test_returns_none_for_no_formats(self):
        """Returns None when no formats available."""
        assert _extract_audio_url({"formats": []}) is None

    def test_fallback_to_format_with_video(self):
        """Falls back to video+audio format when no audio-only available."""
        info = {
            "formats": [
                {"acodec": "mp4a", "vcodec": "h264", "abr": 128, "url": "https://mixed.com"},
            ]
        }
        assert _extract_audio_url(info) == "https://mixed.com"


class TestExtractCaptionsFromInfo:
    """Tests for _extract_captions_from_info helper."""

    def test_returns_segments_from_subtitle_data(self):
        """Extracts caption segments from info dict."""
        info = {
            "requested_subtitles": {
                "en": {
                    "data": [
                        {"start": 0.0, "duration": 5.0, "text": "Hello"},
                    ]
                }
            }
        }
        result = _extract_captions_from_info(info)
        assert result is not None
        assert len(result) == 1
        assert result[0].text == "Hello"

    def test_returns_none_when_no_subtitles(self):
        """Returns None when no requested_subtitles in info."""
        assert _extract_captions_from_info({"requested_subtitles": None}) is None

    def test_returns_none_when_no_english(self):
        """Returns None when no English subtitles available."""
        info = {"requested_subtitles": {"fr": {"data": [{"start": 0, "duration": 1, "text": "Bonjour"}]}}}
        assert _extract_captions_from_info(info) is None
