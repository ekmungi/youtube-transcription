"""Single video row showing title + progress bar or open icon."""

from __future__ import annotations

import os
import subprocess
from typing import Any

import flet as ft

from ui.theme import (
    ACCENT,
    BG_SECONDARY,
    BODY_SIZE,
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
    progress: float | None = None,
    file_path: str | None = None,
    error_message: str | None = None,
    on_retry: Any | None = None,
) -> ft.Container:
    """Build a single job row for the processing or completed section.

    Args:
        title: Video title to display.
        status: One of "waiting", "running", "completed", "failed".
        progress: Progress percentage (0.0 to 1.0) for running status.
        file_path: Path to the saved .md file for completed status.
        error_message: Error text for failed status.
        on_retry: Callback for retry button on failed status.

    Returns:
        A Container representing one job row.
    """
    title_text = ft.Text(
        title, size=BODY_SIZE, color=TEXT_PRIMARY,
        expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
    )

    # Build the trailing widget based on status
    if status == "completed" and file_path:
        trailing = ft.IconButton(
            icon=ft.Icons.OPEN_IN_NEW,
            icon_color=SUCCESS,
            tooltip="Open in Obsidian",
            on_click=lambda e: _open_file(file_path),
        )
    elif status == "running" and progress is not None:
        trailing = ft.Container(
            content=ft.Row(
                controls=[
                    ft.ProgressBar(
                        value=progress, color=ACCENT, bgcolor=BG_SECONDARY, width=150,
                    ),
                    ft.Text(
                        f"{int(progress * 100)}%",
                        size=CAPTION_SIZE, color=TEXT_SECONDARY,
                    ),
                ],
                spacing=PADDING_SM,
            ),
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
            controls=[title_text, trailing],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=BG_SECONDARY,
        border_radius=BORDER_RADIUS,
        padding=ft.padding.symmetric(horizontal=PADDING_SM * 2, vertical=PADDING_SM),
        margin=ft.margin.only(bottom=4),
    )


def _open_file(path: str) -> None:
    """Open a file with the OS default application."""
    if os.name == "nt":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])
