"""Multi-line text area for pasting YouTube URLs (one per line)."""

from __future__ import annotations

from typing import Callable

import flet as ft

from ui.theme import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_BLUE,
    BG_ELEVATED,
    BG_SURFACE,
    BODY_SIZE,
    BORDER,
    BORDER_RADIUS,
    PADDING_MD,
    PADDING_SM,
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
        focused_border_color=ACCENT_BLUE,
        bgcolor=BG_SURFACE,
        border_radius=BORDER_RADIUS,
    )

    def handle_transcribe(e: ft.ControlEvent) -> None:
        """Parse URLs from text area and invoke callback."""
        raw_text = url_field.value or ""
        urls = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if urls:
            on_transcribe(urls)

    def handle_clear(e: ft.ControlEvent) -> None:
        """Clear the URL text area."""
        url_field.value = ""
        url_field.update()

    _btn_size = 40

    transcribe_btn = ft.IconButton(
        icon=ft.Icons.EDIT_NOTE,
        icon_size=20,
        width=_btn_size,
        height=_btn_size,
        tooltip="Transcribe",
        on_click=handle_transcribe,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ACCENT,
                ft.ControlState.HOVERED: ACCENT_HOVER,
            },
            color={"": "#FFFFFF"},
            shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS),
            padding=ft.padding.all(0),
        ),
    )

    clear_btn = ft.IconButton(
        icon=ft.Icons.BACKSPACE_OUTLINED,
        icon_size=18,
        width=_btn_size,
        height=_btn_size,
        tooltip="Clear",
        on_click=handle_clear,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: BG_SURFACE,
                ft.ControlState.HOVERED: BG_ELEVATED,
            },
            color={
                ft.ControlState.DEFAULT: TEXT_SECONDARY,
                ft.ControlState.HOVERED: TEXT_PRIMARY,
            },
            side={ft.ControlState.DEFAULT: ft.BorderSide(1, BORDER)},
            shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS),
            padding=ft.padding.all(0),
        ),
    )

    # Total height: two buttons + spacing
    _total_height = _btn_size * 2 + PADDING_SM

    button_column = ft.Column(
        controls=[transcribe_btn, clear_btn],
        spacing=PADDING_SM,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(content=url_field, expand=True, height=_total_height),
                button_column,
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=PADDING_SM,
        ),
        padding=ft.padding.all(PADDING_MD),
    )
