"""Custom exceptions for the yt-transcribe system."""


class YtTranscribeError(Exception):
    """Base exception for all yt-transcribe errors."""


class VideoNotFoundError(YtTranscribeError):
    """URL is invalid, video deleted, or does not exist."""


class VideoUnavailableError(YtTranscribeError):
    """Video is private, age-restricted, or region-blocked."""


class PlaylistNotFoundError(YtTranscribeError):
    """Playlist URL is invalid or playlist is empty."""


class DownloadError(YtTranscribeError):
    """Network failure during audio download."""


class CaptionNotFoundError(YtTranscribeError):
    """No captions available for this video."""


class TranscriptionError(YtTranscribeError):
    """Whisper or AssemblyAI transcription failed."""
