"""Single video row showing title + progress bar or open icon."""

from __future__ import annotations

import os
import subprocess
from typing import Any

import flet as ft

from ui.theme import (
    ACCENT,
    BG_ELEVATED,
    BG_SURFACE,
    BODY_SIZE,
    BORDER,
    BORDER_RADIUS,
    CAPTION_SIZE,
    ERROR,
    PADDING_SM,
    SUCCESS,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WARNING,
)


def create_job_row(
    title: str,
    status: str,
    phase: str = "",
    file_path: str | None = None,
    error_message: str | None = None,
    on_retry: Any | None = None,
) -> ft.Container:
    """Build a single job row for the processing or completed section.

    Args:
        title: Video title to display.
        status: One of "waiting", "running", "completed", "failed".
        phase: Current phase text (e.g. "downloading", "transcribing").
        file_path: Path to the saved .md file for completed status.
        error_message: Error text for failed status.
        on_retry: Callback for retry button on failed status.

    Returns:
        A Container representing one job row.
    """
    # Status indicator dot
    indicator_color = {
        "waiting": WARNING,
        "running": ACCENT,
        "completed": SUCCESS,
        "failed": ERROR,
    }.get(status, TEXT_SECONDARY)

    indicator = ft.Container(
        width=8,
        height=8,
        border_radius=4,
        bgcolor=indicator_color,
    )

    title_text = ft.Text(
        title, size=BODY_SIZE, color=TEXT_PRIMARY,
        expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
        weight=ft.FontWeight.W_500,
    )

    # Build the trailing widget based on status
    if status == "completed" and file_path:
        trailing = ft.IconButton(
            icon=ft.Icons.OPEN_IN_NEW,
            icon_color=SUCCESS,
            icon_size=16,
            tooltip="Open in Obsidian",
            on_click=lambda e: _open_file(file_path),
        )
    elif status == "running":
        trailing = ft.Row(
            controls=[
                ft.ProgressRing(width=14, height=14, stroke_width=2, color=ACCENT),
                ft.Text(
                    phase or "processing...",
                    size=CAPTION_SIZE, color=ACCENT, italic=True,
                ),
            ],
            spacing=6,
        )
    elif status == "waiting":
        trailing = ft.Text(
            "waiting...", size=CAPTION_SIZE, color=WARNING, italic=True,
        )
    elif status == "failed":
        trailing = ft.Row(
            controls=[
                ft.Text(
                    error_message or "Failed",
                    size=CAPTION_SIZE, color=ERROR, max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=WARNING,
                    icon_size=16,
                    tooltip="Retry",
                    on_click=lambda e: on_retry() if on_retry else None,
                ),
            ],
            spacing=PADDING_SM,
        )
    else:
        trailing = ft.Container()

    return ft.Container(
        content=ft.Row(
            controls=[indicator, title_text, trailing],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        bgcolor=BG_SURFACE,
        border=ft.border.all(1, BORDER),
        border_radius=BORDER_RADIUS,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        margin=ft.margin.only(bottom=6),
    )


def _open_file(path: str) -> None:
    """Open a file with the OS default application."""
    if os.name == "nt":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])
