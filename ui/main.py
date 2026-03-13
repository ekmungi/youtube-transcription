"""Flet desktop app entry point. Wires components, state, and core library."""

from __future__ import annotations

import threading
from dataclasses import replace

import flet as ft

from ui.components.job_row import create_job_row
from ui.components.settings_drawer import create_settings_drawer
from ui.components.title_bar import create_title_bar
from ui.pages.main_page import create_main_page
from ui.state import (
    AppState,
    VideoJob,
    add_processing_job,
    complete_job,
    fail_job,
    update_job_progress,
)
from ui.theme import BG_PRIMARY
from yt_transcribe.config import (
    get_assemblyai_api_key,
    load_config,
    save_config,
    set_assemblyai_api_key,
)
from yt_transcribe.download import get_playlist_info, get_video_info
from yt_transcribe.models import Config, TranscriptionStrategy, WhisperModel
from yt_transcribe.storage import find_existing, save_transcript
from yt_transcribe.transcribe import transcribe_video


def main(page: ft.Page) -> None:
    """Configure window and wire all UI components together.

    Args:
        page: The Flet page instance.
    """
    # Window setup: custom chrome
    page.title = "YT Transcribe"
    page.window.title_bar_hidden = True
    page.window.width = 700
    page.window.height = 600
    page.window.min_width = 500
    page.window.min_height = 400
    page.bgcolor = BG_PRIMARY
    page.padding = 0

    # Mutable state holder (UI thread only)
    state = AppState()

    # Columns for dynamic job rows
    processing_column = ft.Column(spacing=4)
    completed_column = ft.Column(spacing=4)

    def refresh_ui() -> None:
        """Rebuild job rows from current state."""
        processing_column.controls = [
            create_job_row(
                title=j.title,
                status=j.status,
                progress=j.progress if j.status == "running" else None,
                error_message=j.error,
            )
            for j in state.processing
        ]
        completed_column.controls = [
            create_job_row(
                title=j.title,
                status="completed",
                file_path=j.file_path,
            )
            for j in state.completed
        ]
        page.update()

    def handle_settings() -> None:
        """Open the settings drawer on the right."""
        cfg = load_config()
        api_key = get_assemblyai_api_key() or ""

        config_values = {
            "obsidian_vault_path": cfg.obsidian_vault_path,
            "transcript_folder": cfg.transcript_folder,
            "transcription_strategy": cfg.transcription_strategy.value,
            "whisper_model": cfg.whisper_model.value,
            "async_threshold_seconds": cfg.async_threshold_seconds,
            "parallel_enabled": cfg.parallel_enabled,
            "assemblyai_api_key": api_key,
        }

        def on_save(updated: dict) -> None:
            """Save updated config and close drawer."""
            new_config = Config(
                obsidian_vault_path=updated["obsidian_vault_path"],
                transcript_folder=updated["transcript_folder"],
                transcription_strategy=TranscriptionStrategy(
                    updated["transcription_strategy"]
                ),
                whisper_model=WhisperModel(updated["whisper_model"]),
                async_threshold_seconds=updated["async_threshold_seconds"],
                parallel_enabled=updated["parallel_enabled"],
            )
            save_config(new_config)
            if updated.get("assemblyai_api_key"):
                set_assemblyai_api_key(updated["assemblyai_api_key"])
            page.close(page.end_drawer)
            page.update()

        page.end_drawer = create_settings_drawer(config_values, on_save)
        page.open(page.end_drawer)
        page.update()

    def handle_transcribe(urls: list[str], strategy: str, model: str) -> None:
        """Resolve URLs and start transcription in a background thread.

        Args:
            urls: List of YouTube URLs to process.
            strategy: Transcription strategy name.
            model: Whisper model name.
        """
        nonlocal state

        config = load_config()

        def worker() -> None:
            """Background thread: resolve URLs, transcribe, update state."""
            nonlocal state
            cfg = replace(
                config,
                transcription_strategy=TranscriptionStrategy(strategy),
                whisper_model=WhisperModel(model),
            )

            # Resolve all URLs first
            all_videos = []
            for url in urls:
                try:
                    if "playlist" in url.lower():
                        all_videos.extend(get_playlist_info(url))
                    else:
                        all_videos.append(get_video_info(url))
                except Exception as e:
                    state = add_processing_job(
                        state,
                        VideoJob(
                            video_id=url, title=url, url=url,
                            status="failed", error=str(e),
                        ),
                    )
                    refresh_ui()

            # Add all resolved videos to processing
            for vid in all_videos:
                state = add_processing_job(
                    state,
                    VideoJob(video_id=vid.video_id, title=vid.title, url=vid.url),
                )
            refresh_ui()

            # Process one at a time
            for vid in all_videos:
                try:
                    cached = find_existing(cfg, vid.video_id)
                    if cached is not None:
                        state = complete_job(state, vid.video_id, str(cached))
                        refresh_ui()
                        continue

                    state = update_job_progress(state, vid.video_id, 0.1)
                    refresh_ui()

                    transcript = transcribe_video(vid, cfg)
                    saved_path = save_transcript(cfg, transcript)

                    state = complete_job(state, vid.video_id, str(saved_path))
                except Exception as e:
                    state = fail_job(state, vid.video_id, str(e))
                refresh_ui()

            state = replace(state, is_transcribing=False)

        state = replace(state, is_transcribing=True)
        threading.Thread(target=worker, daemon=True).start()

    # Build layout
    title_bar = create_title_bar(page, on_settings=handle_settings)

    main_page = create_main_page(
        on_transcribe=handle_transcribe,
        processing_column=processing_column,
        completed_column=completed_column,
    )

    page.add(
        ft.Column(
            controls=[title_bar, main_page],
            expand=True,
            spacing=0,
        )
    )


if __name__ == "__main__":
    ft.run(main)
