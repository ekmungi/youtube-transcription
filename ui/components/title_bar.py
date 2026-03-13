"""Custom window title bar with drag area, settings gear, and window controls."""

from __future__ import annotations

from typing import Callable

import flet as ft

from ui.theme import (
    BG_PRIMARY,
    ICON_BUTTON_STYLE,
    PADDING_SM,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TITLE_BAR_HEIGHT,
    TITLE_SIZE,
)


def create_title_bar(
    page: ft.Page,
    on_settings: Callable[[], None],
) -> ft.Container:
    """Build the custom title bar with drag area and window controls.

    Args:
        page: The Flet page for window operations.
        on_settings: Callback when gear icon is clicked.

    Returns:
        A Container with the complete title bar.
    """

    def minimize_click(e: ft.ControlEvent) -> None:
        """Minimize the window."""
        page.window.minimized = True
        page.update()

    def maximize_click(e: ft.ControlEvent) -> None:
        """Toggle maximize/restore."""
        page.window.maximized = not page.window.maximized
        page.update()

    def close_click(e: ft.ControlEvent) -> None:
        """Close the window."""
        page.window.close()

    title_text = ft.Text(
        "YT Transcribe",
        size=TITLE_SIZE,
        color=TEXT_PRIMARY,
        weight=ft.FontWeight.W_600,
    )

    gear_button = ft.IconButton(
        icon=ft.Icons.SETTINGS,
        icon_color=TEXT_SECONDARY,
        style=ICON_BUTTON_STYLE,
        tooltip="Settings",
        on_click=lambda e: on_settings(),
    )

    minimize_btn = ft.IconButton(
        icon=ft.Icons.MINIMIZE,
        icon_color=TEXT_SECONDARY,
        style=ICON_BUTTON_STYLE,
        tooltip="Minimize",
        on_click=minimize_click,
    )

    maximize_btn = ft.IconButton(
        icon=ft.Icons.CROP_SQUARE,
        icon_color=TEXT_SECONDARY,
        style=ICON_BUTTON_STYLE,
        tooltip="Maximize",
        on_click=maximize_click,
    )

    close_btn = ft.IconButton(
        icon=ft.Icons.CLOSE,
        icon_color=TEXT_SECONDARY,
        style=ICON_BUTTON_STYLE,
        tooltip="Close",
        on_click=close_click,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.WindowDragArea(
                    content=ft.Row(
                        controls=[title_text],
                        expand=True,
                    ),
                    expand=True,
                ),
                gear_button,
                minimize_btn,
                maximize_btn,
                close_btn,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=BG_PRIMARY,
        height=TITLE_BAR_HEIGHT,
        padding=ft.padding.symmetric(horizontal=PADDING_SM),
    )
