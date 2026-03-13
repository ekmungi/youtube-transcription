"""Multi-line text area for pasting YouTube URLs (one per line)."""

from __future__ import annotations

from typing import Callable

import flet as ft

from ui.theme import (
    ACCENT,
    BG_SECONDARY,
    BODY_SIZE,
    BORDER,
    BORDER_RADIUS,
    BUTTON_STYLE,
    PADDING_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def create_url_input(
    on_transcribe: Callable[[list[str]], None],
) -> ft.Container:
    """Build the URL input area with a Transcribe button.

    Args:
        on_transcribe: Callback with list of URLs when button is clicked.

    Returns:
        A Container with the text area and button.
    """
    url_field = ft.TextField(
        multiline=True,
        min_lines=3,
        max_lines=6,
        hint_text="Paste YouTube URLs here (one per line)...",
        hint_style=ft.TextStyle(color=TEXT_SECONDARY, size=BODY_SIZE),
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        border_color=BORDER,
        focused_border_color=ACCENT,
        bgcolor=BG_SECONDARY,
        border_radius=BORDER_RADIUS,
    )

    def handle_transcribe(e: ft.ControlEvent) -> None:
        """Parse URLs from text area and invoke callback."""
        raw_text = url_field.value or ""
        urls = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if urls:
            on_transcribe(urls)

    transcribe_btn = ft.ElevatedButton(
        text="Transcribe",
        style=BUTTON_STYLE,
        on_click=handle_transcribe,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(content=url_field, expand=True),
                transcribe_btn,
            ],
            vertical_alignment=ft.CrossAxisAlignment.END,
            spacing=PADDING_MD,
        ),
        padding=ft.padding.all(PADDING_MD),
    )
