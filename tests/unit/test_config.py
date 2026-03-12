"""Tests for config loading, saving, and validation."""

from pathlib import Path

import pytest
import yaml

from yt_transcribe.config import (
    get_assemblyai_api_key,
    load_config,
    save_config,
    DEFAULT_CONFIG,
)
from yt_transcribe.models import Config, TranscriptionStrategy, WhisperModel


class TestLoadConfig:
    def test_load_from_file(self, tmp_path: Path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "version": 1,
            "obsidian_vault_path": "/my/vault",
            "transcript_folder": "YT",
            "transcription_strategy": "cloud",
            "whisper_model": "small",
            "async_threshold_seconds": 60,
            "parallel_enabled": True,
        }))
        config = load_config(config_file)
        assert config.obsidian_vault_path == "/my/vault"
        assert config.transcription_strategy == TranscriptionStrategy.CLOUD
        assert config.whisper_model == WhisperModel.SMALL
        assert config.parallel_enabled is True

    def test_load_missing_file_returns_defaults(self, tmp_path: Path):
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config == DEFAULT_CONFIG

    def test_load_partial_file_fills_defaults(self, tmp_path: Path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "version": 1,
            "obsidian_vault_path": "/custom",
        }))
        config = load_config(config_file)
        assert config.obsidian_vault_path == "/custom"
        assert config.whisper_model == WhisperModel.BASE  # default

    def test_load_fixture(self):
        fixture = Path(__file__).parent.parent / "fixtures" / "sample_config.yaml"
        config = load_config(fixture)
        assert config.obsidian_vault_path == "C:/TestVault"


class TestSaveConfig:
    def test_save_and_reload(self, tmp_path: Path):
        config_file = tmp_path / "config.yaml"
        config = Config(
            obsidian_vault_path="/vault",
            transcript_folder="T",
            transcription_strategy=TranscriptionStrategy.LOCAL,
            whisper_model=WhisperModel.TINY,
            async_threshold_seconds=300,
            parallel_enabled=False,
        )
        save_config(config, config_file)
        reloaded = load_config(config_file)
        assert reloaded == config

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        config_file = tmp_path / "subdir" / "config.yaml"
        save_config(DEFAULT_CONFIG, config_file)
        assert config_file.exists()

    def test_save_includes_version(self, tmp_path: Path):
        config_file = tmp_path / "config.yaml"
        save_config(DEFAULT_CONFIG, config_file)
        raw = yaml.safe_load(config_file.read_text())
        assert raw["version"] == 1


class TestGetAssemblyaiApiKey:
    def test_from_env_var(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key-123")
        assert get_assemblyai_api_key() == "test-key-123"

    def test_returns_none_when_not_set(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)
        # Also mock keyring to return None
        import unittest.mock
        with unittest.mock.patch("yt_transcribe.config._get_keyring_key", return_value=None):
            assert get_assemblyai_api_key() is None
