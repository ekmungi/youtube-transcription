"""Config loading, saving, and validation for ~/.yt-transcribe/config.yaml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from yt_transcribe.models import Config, TranscriptionStrategy, WhisperModel

# Default config file location
CONFIG_DIR = Path.home() / ".yt-transcribe"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
CONFIG_VERSION = 1

# Default configuration values
DEFAULT_CONFIG = Config(
    obsidian_vault_path=str(Path.home() / "Obsidian"),
    transcript_folder="Sources/YouTube Transcripts",
    transcription_strategy=TranscriptionStrategy.AUTO,
    whisper_model=WhisperModel.BASE,
    async_threshold_seconds=180,
    parallel_enabled=False,
    ffmpeg_location="",
)

_FIELD_DEFAULTS: dict[str, Any] = {
    "obsidian_vault_path": DEFAULT_CONFIG.obsidian_vault_path,
    "transcript_folder": DEFAULT_CONFIG.transcript_folder,
    "transcription_strategy": DEFAULT_CONFIG.transcription_strategy.value,
    "whisper_model": DEFAULT_CONFIG.whisper_model.value,
    "async_threshold_seconds": DEFAULT_CONFIG.async_threshold_seconds,
    "parallel_enabled": DEFAULT_CONFIG.parallel_enabled,
    "ffmpeg_location": DEFAULT_CONFIG.ffmpeg_location,
}


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load config from YAML file. Returns defaults if file missing."""
    if not path.exists():
        return DEFAULT_CONFIG

    raw = yaml.safe_load(path.read_text()) or {}

    return Config(
        obsidian_vault_path=raw.get("obsidian_vault_path", _FIELD_DEFAULTS["obsidian_vault_path"]),
        transcript_folder=raw.get("transcript_folder", _FIELD_DEFAULTS["transcript_folder"]),
        transcription_strategy=TranscriptionStrategy(
            raw.get("transcription_strategy", _FIELD_DEFAULTS["transcription_strategy"])
        ),
        whisper_model=WhisperModel(
            raw.get("whisper_model", _FIELD_DEFAULTS["whisper_model"])
        ),
        async_threshold_seconds=int(
            raw.get("async_threshold_seconds", _FIELD_DEFAULTS["async_threshold_seconds"])
        ),
        parallel_enabled=bool(
            raw.get("parallel_enabled", _FIELD_DEFAULTS["parallel_enabled"])
        ),
        ffmpeg_location=str(
            raw.get("ffmpeg_location", _FIELD_DEFAULTS["ffmpeg_location"])
        ),
    )


def save_config(config: Config, path: Path = CONFIG_PATH) -> None:
    """Save config to YAML file. Creates parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": CONFIG_VERSION,
        "obsidian_vault_path": config.obsidian_vault_path,
        "transcript_folder": config.transcript_folder,
        "transcription_strategy": config.transcription_strategy.value,
        "whisper_model": config.whisper_model.value,
        "async_threshold_seconds": config.async_threshold_seconds,
        "parallel_enabled": config.parallel_enabled,
        "ffmpeg_location": config.ffmpeg_location,
    }

    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def _get_keyring_key() -> str | None:
    """Attempt to retrieve AssemblyAI key from OS keyring."""
    try:
        import keyring
        return keyring.get_password("yt-transcribe", "assemblyai_api_key")
    except Exception:
        return None


def get_assemblyai_api_key() -> str | None:
    """Resolve AssemblyAI API key: env var first, then OS keyring."""
    env_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if env_key:
        return env_key
    return _get_keyring_key()


def set_assemblyai_api_key(key: str) -> None:
    """Store AssemblyAI API key in OS keyring."""
    import keyring
    keyring.set_password("yt-transcribe", "assemblyai_api_key", key)
