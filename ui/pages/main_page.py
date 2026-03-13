"""Main page layout: URL input, strategy dropdowns, processing and completed sections."""

from __future__ import annotations

from typing import Callable

import flet as ft

from ui.components.url_input import create_url_input
from ui.theme import (
    ACCENT,
    BG_PRIMARY,
    BODY_SIZE,
    BORDER,
    HEADING_SIZE,
    PADDING_LG,
    PADDING_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from yt_transcribe.models import TranscriptionStrategy, WhisperModel


def _section_header(label: str) -> ft.Container:
    """Create a section divider with a label.

    Args:
        label: Section heading text.

    Returns:
        Styled container with heading and divider line.
    """
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(
                    label, size=HEADING_SIZE, color=TEXT_SECONDARY,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Container(
                    content=ft.Divider(color=BORDER),
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=PADDING_MD,
        ),
        padding=ft.padding.only(top=PADDING_LG, bottom=PADDING_MD),
    )


def create_main_page(
    on_transcribe: Callable[[list[str], str, str], None],
    processing_column: ft.Column,
    completed_column: ft.Column,
) -> ft.Container:
    """Build the main page layout.

    Args:
        on_transcribe: Callback(urls, strategy, model) when Transcribe is clicked.
        processing_column: Column ref for dynamically adding processing job rows.
        completed_column: Column ref for dynamically adding completed job rows.

    Returns:
        A Container with the full main page.
    """
    strategy_dropdown = ft.Dropdown(
        label="Strategy",
        value=TranscriptionStrategy.AUTO.value,
        options=[ft.dropdown.Option(s.value) for s in TranscriptionStrategy],
        width=160,
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT,
    )

    model_dropdown = ft.Dropdown(
        label="Model",
        value=WhisperModel.BASE.value,
        options=[ft.dropdown.Option(m.value) for m in WhisperModel],
        width=140,
        text_style=ft.TextStyle(color=TEXT_PRIMARY, size=BODY_SIZE),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=BORDER,
        focused_border_color=ACCENT,
    )

    def handle_transcribe(urls: list[str]) -> None:
        """Forward URLs with selected strategy and model."""
        on_transcribe(
            urls,
            strategy_dropdown.value or "auto",
            model_dropdown.value or "base",
        )

    url_input = create_url_input(on_transcribe=handle_transcribe)

    dropdowns_row = ft.Row(
        controls=[strategy_dropdown, model_dropdown],
        spacing=PADDING_MD,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                url_input,
                ft.Container(
                    content=dropdowns_row,
                    padding=ft.padding.symmetric(horizontal=PADDING_MD),
                ),
                _section_header("Processing"),
                ft.Container(
                    content=processing_column,
                    padding=ft.padding.symmetric(horizontal=PADDING_MD),
                ),
                _section_header("Completed"),
                ft.Container(
                    content=completed_column,
                    padding=ft.padding.symmetric(horizontal=PADDING_MD),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        bgcolor=BG_PRIMARY,
        expand=True,
    )
