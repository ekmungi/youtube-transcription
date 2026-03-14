"""Slide-out settings panel from the right side of the window."""

from __future__ import annotations

import subprocess
import threading
from typing import Callable

import flet as ft

from ui.theme import (
    ACCENT_BLUE,
    BG_PRIMARY,
    BG_SURFACE,
    BODY_SIZE,
    BORDER,
    BORDER_RADIUS,
    BUTTON_STYLE,
    BUTTON_STYLE_SECONDARY,
    CAPTION_SIZE,
    DRAWER_WIDTH,
    PADDING_LG,
    PADDING_SM,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from yt_transcribe.models import WhisperModel


def _section_title(text: str) -> ft.Text:
    """Section title matching ai-meeting-notes .form-section-title."""
    return ft.Text(
        text, size=BODY_SIZE, color=TEXT_SECONDARY, weight=ft.FontWeight.W_500,
    )


def _styled_dropdown(label: str, value: str, options: list[str]) -> ft.Dropdown:
    """Create a dropdown styled to match the dark theme.

    Args:
        label: Dropdown label text.
        value: Currently selected value.
        options: List of option strings.

    Returns:
        Styled Dropdown control with square trailing icon.
    """
    return ft.Dropdown(
        label=label,
        value=value,
        options=[ft.dropdown.Option(o) for o in options],
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT_BLUE,
        bgcolor=BG_SURFACE,
        border_radius=BORDER_RADIUS,
        trailing_icon=ft.Icons.KEYBOARD_ARROW_DOWN,
    )


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
    # -- Output folder (text field + browse button) ----------------------------

    folder_field = ft.TextField(
        label="Output folder",
        value=config_values.get("obsidian_vault_path", ""),
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT_BLUE,
        bgcolor=BG_SURFACE,
        border_radius=BORDER_RADIUS,
        expand=True,
    )

    def _browse_folder(e: ft.ControlEvent) -> None:
        """Open native Windows folder dialog via PowerShell."""
        def _pick() -> None:
            try:
                result = subprocess.run(
                    [
                        "powershell", "-WindowStyle", "Hidden", "-Command",
                        (
                            "Add-Type -AssemblyName System.Windows.Forms; "
                            "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                            "$f.Description = 'Select output folder'; "
                            "if ($f.ShowDialog() -eq 'OK') { $f.SelectedPath }"
                        ),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                path = result.stdout.strip()
                if path:
                    folder_field.value = path
                    folder_field.update()
            except Exception:
                pass
        threading.Thread(target=_pick, daemon=True).start()

    browse_btn = ft.Container(
        content=ft.Icon(ft.Icons.FOLDER_OPEN, size=16, color=TEXT_SECONDARY),
        width=36,
        height=36,
        bgcolor=BG_SURFACE,
        border=ft.border.all(1, BORDER),
        border_radius=BORDER_RADIUS,
        alignment=ft.Alignment(0, 0),
        on_click=_browse_folder,
        tooltip="Browse for folder",
        on_hover=lambda e: _hover_browse(e, browse_btn),
    )

    folder_row = ft.Row(
        controls=[folder_field, browse_btn],
        spacing=PADDING_SM,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # -- Whisper model --------------------------------------------------------

    model_dropdown = _styled_dropdown(
        label="Whisper model size",
        value=config_values.get("whisper_model", "base"),
        options=[m.value for m in WhisperModel],
    )

    # -- Cloud API key --------------------------------------------------------

    api_key_field = ft.TextField(
        label="API key (AssemblyAI)",
        value=config_values.get("assemblyai_api_key", ""),
        password=True,
        can_reveal_password=True,
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT_BLUE,
        bgcolor=BG_SURFACE,
        border_radius=BORDER_RADIUS,
    )

    # -- FFmpeg path ----------------------------------------------------------

    ffmpeg_field = ft.TextField(
        label="FFmpeg path",
        value=config_values.get("ffmpeg_location", ""),
        hint_text="Leave empty to use system PATH",
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT_BLUE,
        bgcolor=BG_SURFACE,
        border_radius=BORDER_RADIUS,
        expand=True,
    )

    def _browse_ffmpeg(e: ft.ControlEvent) -> None:
        """Open native Windows file dialog to pick ffmpeg executable."""
        def _pick() -> None:
            try:
                result = subprocess.run(
                    [
                        "powershell", "-WindowStyle", "Hidden", "-Command",
                        (
                            "Add-Type -AssemblyName System.Windows.Forms; "
                            "$f = New-Object System.Windows.Forms.OpenFileDialog; "
                            "$f.Title = 'Select ffmpeg executable'; "
                            "$f.Filter = 'ffmpeg|ffmpeg.exe|All files|*.*'; "
                            "if ($f.ShowDialog() -eq 'OK') { $f.FileName }"
                        ),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                path = result.stdout.strip()
                if path:
                    ffmpeg_field.value = path
                    ffmpeg_field.update()
            except Exception:
                pass
        threading.Thread(target=_pick, daemon=True).start()

    ffmpeg_browse_btn = ft.Container(
        content=ft.Icon(ft.Icons.FOLDER_OPEN, size=16, color=TEXT_SECONDARY),
        width=36,
        height=36,
        bgcolor=BG_SURFACE,
        border=ft.border.all(1, BORDER),
        border_radius=BORDER_RADIUS,
        alignment=ft.Alignment(0, 0),
        on_click=_browse_ffmpeg,
        tooltip="Browse for ffmpeg",
        on_hover=lambda e: _hover_browse(e, ffmpeg_browse_btn),
    )

    ffmpeg_row = ft.Row(
        controls=[ffmpeg_field, ffmpeg_browse_btn],
        spacing=PADDING_SM,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # -- Advanced -------------------------------------------------------------

    threshold_value = int(config_values.get("async_threshold_seconds", 180))
    # Clamp to slider range to prevent Flet ValueError
    threshold_max = 7200
    threshold_value = min(max(threshold_value, 30), threshold_max)

    threshold_label = ft.Text(
        f"Async threshold: {threshold_value}s",
        size=CAPTION_SIZE, color=TEXT_SECONDARY,
    )

    threshold_slider = ft.Slider(
        min=30,
        max=threshold_max,
        divisions=None,
        value=threshold_value,
        active_color=ACCENT_BLUE,
        on_change=lambda e: _update_threshold_label(e, threshold_label),
    )

    parallel_switch = ft.Switch(
        label="Parallel processing (cloud only)",
        value=config_values.get("parallel_enabled", False),
        active_color=ACCENT_BLUE,
    )

    # -- Save button ----------------------------------------------------------

    def handle_save(e: ft.ControlEvent) -> None:
        """Collect field values and invoke save callback."""
        updated = {
            "obsidian_vault_path": folder_field.value,
            "transcript_folder": "",
            "transcription_strategy": config_values.get("transcription_strategy", "auto"),
            "assemblyai_api_key": api_key_field.value,
            "whisper_model": model_dropdown.value,
            "async_threshold_seconds": int(threshold_slider.value or 180),
            "parallel_enabled": parallel_switch.value,
            "ffmpeg_location": ffmpeg_field.value or "",
        }
        on_save(updated)

    save_btn = ft.ElevatedButton(
        content=ft.Text("Save", weight=ft.FontWeight.W_500),
        style=BUTTON_STYLE,
        on_click=handle_save,
    )

    # -- Layout ---------------------------------------------------------------

    heading = ft.Text(
        "Settings", size=15, color=TEXT_PRIMARY, weight=ft.FontWeight.W_600,
    )

    return ft.NavigationDrawer(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        heading,
                        ft.Divider(color=BORDER),
                        _section_title("Output"),
                        folder_row,
                        ft.Divider(color=BORDER),
                        _section_title("Local transcription"),
                        model_dropdown,
                        ft.Divider(color=BORDER),
                        _section_title("Cloud transcription"),
                        api_key_field,
                        ft.Divider(color=BORDER),
                        _section_title("FFmpeg"),
                        ffmpeg_row,
                        ft.Divider(color=BORDER),
                        _section_title("Advanced"),
                        threshold_label,
                        threshold_slider,
                        parallel_switch,
                        ft.Container(height=PADDING_SM),
                        save_btn,
                    ],
                    spacing=PADDING_SM,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=ft.padding.all(PADDING_LG),
                width=DRAWER_WIDTH,
                bgcolor=BG_PRIMARY,
            ),
        ],
        bgcolor=BG_PRIMARY,
    )


def _update_threshold_label(e: ft.ControlEvent, label: ft.Text) -> None:
    """Update the threshold label when the slider changes."""
    label.value = f"Async threshold: {int(e.control.value)}s"
    label.update()


def _hover_browse(e: ft.ControlEvent, container: ft.Container) -> None:
    """Toggle browse button background on hover."""
    from ui.theme import BG_ELEVATED
    container.bgcolor = BG_ELEVATED if e.data == "true" else BG_SURFACE
    container.update()
