"""Slide-out settings panel from the right side of the window."""

from __future__ import annotations

from typing import Callable

import flet as ft

from ui.theme import (
    ACCENT,
    BG_SECONDARY,
    BODY_SIZE,
    BORDER,
    BUTTON_STYLE,
    DRAWER_WIDTH,
    HEADING_SIZE,
    PADDING_LG,
    PADDING_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from yt_transcribe.models import TranscriptionStrategy, WhisperModel


def create_settings_drawer(
    config_values: dict,
    on_save: Callable[[dict], None],
) -> ft.NavigationDrawer:
    """Build the settings drawer that slides from the right.

    Args:
        config_values: Current config as a dict with string values.
        on_save: Callback with updated config dict when Save is clicked.

    Returns:
        A NavigationDrawer configured as a settings panel.
    """
    vault_field = ft.TextField(
        label="Obsidian Vault Path",
        value=config_values.get("obsidian_vault_path", ""),
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT,
        bgcolor=BG_SECONDARY,
    )

    folder_field = ft.TextField(
        label="Transcript Folder",
        value=config_values.get("transcript_folder", ""),
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT,
        bgcolor=BG_SECONDARY,
    )

    strategy_dropdown = ft.Dropdown(
        label="Transcription Strategy",
        value=config_values.get("transcription_strategy", "auto"),
        options=[ft.dropdown.Option(s.value) for s in TranscriptionStrategy],
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT,
        bgcolor=BG_SECONDARY,
    )

    api_key_field = ft.TextField(
        label="AssemblyAI API Key",
        value=config_values.get("assemblyai_api_key", ""),
        password=True,
        can_reveal_password=True,
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT,
        bgcolor=BG_SECONDARY,
    )

    model_dropdown = ft.Dropdown(
        label="Whisper Model",
        value=config_values.get("whisper_model", "base"),
        options=[ft.dropdown.Option(m.value) for m in WhisperModel],
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT,
        bgcolor=BG_SECONDARY,
    )

    threshold_slider = ft.Slider(
        min=30,
        max=600,
        divisions=19,
        value=int(config_values.get("async_threshold_seconds", 180)),
        label="Async threshold: {value}s",
        active_color=ACCENT,
    )

    parallel_switch = ft.Switch(
        label="Parallel Processing (cloud only)",
        value=config_values.get("parallel_enabled", False),
        active_color=ACCENT,
        label_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
    )

    def handle_save(e: ft.ControlEvent) -> None:
        """Collect field values and invoke save callback."""
        updated = {
            "obsidian_vault_path": vault_field.value,
            "transcript_folder": folder_field.value,
            "transcription_strategy": strategy_dropdown.value,
            "assemblyai_api_key": api_key_field.value,
            "whisper_model": model_dropdown.value,
            "async_threshold_seconds": int(threshold_slider.value or 180),
            "parallel_enabled": parallel_switch.value,
        }
        on_save(updated)

    save_btn = ft.ElevatedButton(
        text="Save",
        style=BUTTON_STYLE,
        on_click=handle_save,
    )

    heading = ft.Text(
        "Settings",
        size=HEADING_SIZE,
        color=TEXT_PRIMARY,
        weight=ft.FontWeight.W_600,
    )

    return ft.NavigationDrawer(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        heading,
                        ft.Divider(color=BORDER),
                        vault_field,
                        folder_field,
                        strategy_dropdown,
                        api_key_field,
                        model_dropdown,
                        ft.Text(
                            f"Async threshold: {int(threshold_slider.value or 180)}s",
                            size=BODY_SIZE, color=TEXT_SECONDARY,
                        ),
                        threshold_slider,
                        parallel_switch,
                        ft.Container(height=PADDING_MD),
                        save_btn,
                    ],
                    spacing=PADDING_MD,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=ft.padding.all(PADDING_LG),
                width=DRAWER_WIDTH,
            ),
        ],
        bgcolor=BG_SECONDARY,
    )
