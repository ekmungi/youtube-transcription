"""Flet desktop app entry point. Wires components, state, and core library."""

from __future__ import annotations

import logging
import sys
import threading
from dataclasses import replace
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")

import flet as ft


def _resolve_icon_path() -> str:
    """Resolve the app icon path for both dev and PyInstaller-bundled modes."""
    if getattr(sys, "frozen", False):
        return str(Path(sys._MEIPASS) / "assets" / "icon.png")
    return str(Path(__file__).parent.parent / "assets" / "icon.png")

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
    update_job_phase,
)
from ui.theme import BG_PRIMARY, FONT_FAMILY
from yt_transcribe.config import (
    get_assemblyai_api_key,
    load_config,
    save_config,
    set_assemblyai_api_key,
)
from yt_transcribe.download import extract_video_data, get_playlist_info
from yt_transcribe.models import Config, TranscriptionStrategy, WhisperModel
from yt_transcribe.storage import find_existing, save_transcript
from yt_transcribe.transcribe import transcribe_video_fast


def main(page: ft.Page) -> None:
    """Configure window and wire all UI components together.

    Args:
        page: The Flet page instance.
    """
    # Window setup: custom chrome + icon
    page.title = "YT Transcribe"
    page.window.icon = _resolve_icon_path()
    page.window.title_bar_hidden = True
    page.window.width = 700
    page.window.height = 600
    page.window.min_width = 500
    page.window.min_height = 400
    page.bgcolor = BG_PRIMARY
    page.padding = 0
    page.fonts = {
        "Fira Sans": "https://raw.githubusercontent.com/google/fonts/main/ofl/firasans/FiraSans-Regular.ttf",
    }
    page.theme = ft.Theme(
        font_family=FONT_FAMILY,
        visual_density=ft.VisualDensity.COMPACT,
    )

    # Mutable state holder (UI thread only)
    state = AppState()

    # Columns for dynamic job rows
    processing_column = ft.Column(spacing=6)
    completed_column = ft.Column(spacing=6)

    def refresh_ui() -> None:
        """Rebuild job rows from current state, scheduled on the UI thread."""
        async def _do_refresh() -> None:
            processing_column.controls = [
                create_job_row(
                    title=j.title,
                    status=j.status,
                    phase=j.phase,
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
        page.run_task(_do_refresh)

    # -- Settings drawer (created once, toggled on/off) -----------------------

    def _build_drawer() -> ft.NavigationDrawer:
        """Build the settings drawer with current config values."""
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
            "ffmpeg_location": cfg.ffmpeg_location,
        }
        return create_settings_drawer(config_values, on_save=_on_settings_save)

    def _on_settings_save(updated: dict) -> None:
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
            ffmpeg_location=updated.get("ffmpeg_location", ""),
        )
        save_config(new_config)
        if updated.get("assemblyai_api_key"):
            set_assemblyai_api_key(updated["assemblyai_api_key"])
        page.update()

    async def handle_settings() -> None:
        """Rebuild and open the settings drawer."""
        page.end_drawer = _build_drawer()
        await page.show_end_drawer()
        page.update()

    # -- Transcription handler ------------------------------------------------

    def handle_transcribe(urls: list[str], strategy: str = "auto") -> None:
        """Resolve URLs and start transcription in a background thread.

        Args:
            urls: List of YouTube URLs to process.
            strategy: Transcription strategy selected in the UI.
        """
        nonlocal state

        config = replace(
            load_config(),
            transcription_strategy=TranscriptionStrategy(strategy),
        )

        def worker() -> None:
            """Background thread: resolve URLs, transcribe, update state."""
            nonlocal state

            # Resolve all URLs first
            all_videos = []
            video_data_map = {}  # video_id -> VideoData for optimized transcription
            for url in urls:
                try:
                    if "playlist" in url.lower():
                        all_videos.extend(get_playlist_info(url))
                    else:
                        vdata = extract_video_data(url)
                        all_videos.append(vdata.video_info)
                        video_data_map[vdata.video_info.video_id] = vdata
                except Exception as e:
                    state = add_processing_job(
                        state,
                        VideoJob(
                            video_id=url, title=url, url=url,
                            status="failed", error=str(e),
                        ),
                    )
                    refresh_ui()

            # Add resolved videos, skipping any already in processing
            existing_ids = {j.video_id for j in state.processing}
            new_videos = [v for v in all_videos if v.video_id not in existing_ids]
            for vid in new_videos:
                state = add_processing_job(
                    state,
                    VideoJob(video_id=vid.video_id, title=vid.title, url=vid.url),
                )
            all_videos = new_videos
            refresh_ui()

            # Process one at a time
            for vid in all_videos:
                try:
                    cached = find_existing(config, vid.video_id)
                    if cached is not None:
                        state = complete_job(state, vid.video_id, str(cached))
                        refresh_ui()
                        continue

                    def _on_phase(text: str, _vid_id=vid.video_id) -> None:
                        """Update phase text in UI."""
                        nonlocal state
                        state = update_job_phase(state, _vid_id, text)
                        refresh_ui()

                    # Use pre-fetched VideoData if available, otherwise fetch now
                    vdata = video_data_map.get(vid.video_id)
                    if vdata is None:
                        _on_phase("fetching video data...")
                        vdata = extract_video_data(vid.url)

                    transcript = transcribe_video_fast(vdata, config, phase_callback=_on_phase)

                    _on_phase("saving...")

                    saved_path = save_transcript(config, transcript)
                    state = complete_job(state, vid.video_id, str(saved_path))
                except Exception as e:
                    state = fail_job(state, vid.video_id, str(e))
                refresh_ui()

            state = replace(state, is_transcribing=False)

        state = replace(state, is_transcribing=True)
        threading.Thread(target=worker, daemon=True).start()

    # -- Build layout ---------------------------------------------------------

    title_bar = create_title_bar(page, on_settings=handle_settings)

    # Set initial drawer so page knows about it
    page.end_drawer = _build_drawer()

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
