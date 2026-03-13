"""Custom window title bar with drag area, settings gear, and window controls.

Matches ai-meeting-notes design: square 28x28 controls with 6px radius.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Union

import flet as ft

from ui.theme import (
    BG_ELEVATED,
    BG_PRIMARY,
    BORDER_RADIUS,
    PADDING_SM,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TITLE_BAR_HEIGHT,
    TITLE_SIZE,
)

# Window control button size (matches ai-meeting-notes .title-bar__ctrl)
_CTRL_SIZE = 28


def _title_ctrl(
    icon: str,
    tooltip: str,
    on_click: Callable,
    hover_bgcolor: str = BG_ELEVATED,
    hover_color: str = TEXT_PRIMARY,
) -> ft.IconButton:
    """Create a square window control button.

    Args:
        icon: Flet icon name.
        tooltip: Tooltip text.
        on_click: Click handler.
        hover_bgcolor: Background color on hover.
        hover_color: Icon color on hover.

    Returns:
        Styled IconButton matching ai-meeting-notes title bar controls.
    """
    return ft.IconButton(
        icon=icon,
        icon_color=TEXT_SECONDARY,
        icon_size=14,
        width=_CTRL_SIZE,
        height=_CTRL_SIZE,
        style=ft.ButtonStyle(
            color={
                ft.ControlState.DEFAULT: TEXT_SECONDARY,
                ft.ControlState.HOVERED: hover_color,
            },
            bgcolor={
                ft.ControlState.HOVERED: hover_bgcolor,
            },
            shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS),
            padding=ft.padding.all(0),
        ),
        tooltip=tooltip,
        on_click=on_click,
    )


def create_title_bar(
    page: ft.Page,
    on_settings: Callable[[], Awaitable[None]],
) -> ft.Container:
    """Build the custom title bar with drag area and window controls.

    Args:
        page: The Flet page for window operations.
        on_settings: Async callback when gear icon is clicked.

    Returns:
        A Container with the complete title bar.
    """

    def minimize_click(e: ft.ControlEvent) -> None:
        """Minimize the window."""
        page.window.minimized = True
        page.update()

    async def close_click(e: ft.ControlEvent) -> None:
        """Close the window."""
        await page.window.close()

    async def settings_click(e: ft.ControlEvent) -> None:
        """Open the settings drawer."""
        await on_settings()

    title_text = ft.Text(
        "YT Transcribe",
        size=TITLE_SIZE,
        color=TEXT_PRIMARY,
        weight=ft.FontWeight.W_600,
    )

    version_text = ft.Text(
        "v0.1",
        size=11,
        color=TEXT_MUTED,
    )

    gear_button = _title_ctrl(
        icon=ft.Icons.SETTINGS,
        tooltip="Settings",
        on_click=settings_click,
    )

    minimize_btn = _title_ctrl(
        icon=ft.Icons.MINIMIZE,
        tooltip="Minimize",
        on_click=minimize_click,
    )

    close_btn = _title_ctrl(
        icon=ft.Icons.CLOSE,
        tooltip="Close",
        on_click=close_click,
        hover_bgcolor="#C0392B",
        hover_color="#FFFFFF",
    )

    controls_row = ft.Row(
        controls=[gear_button, minimize_btn, close_btn],
        spacing=2,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.WindowDragArea(
                    content=ft.Row(
                        controls=[title_text, version_text],
                        spacing=8,
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    expand=True,
                ),
                controls_row,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=BG_PRIMARY,
        height=TITLE_BAR_HEIGHT,
        padding=ft.padding.only(left=16, right=8, top=6, bottom=6),
    )
