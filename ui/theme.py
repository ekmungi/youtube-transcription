"""Dark theme constants for the YT Transcribe desktop app."""

from __future__ import annotations

import flet as ft


# -- Colors -------------------------------------------------------------------

BG_PRIMARY = "#1a1a2e"          # Main background
BG_SECONDARY = "#16213e"        # Cards, panels
BG_SURFACE = "#0f3460"          # Elevated surfaces
ACCENT = "#e94560"              # Primary accent (buttons, active states)
ACCENT_HOVER = "#ff6b6b"        # Accent hover state
TEXT_PRIMARY = "#eaeaea"         # Main text
TEXT_SECONDARY = "#a0a0b0"      # Muted text
TEXT_DISABLED = "#555566"        # Disabled text
BORDER = "#2a2a4a"              # Borders and dividers
SUCCESS = "#4ecca3"             # Completed, success states
ERROR = "#ff4444"               # Error states
WARNING = "#ffc107"             # Warnings

# -- Typography ---------------------------------------------------------------

FONT_FAMILY = "Segoe UI"
TITLE_SIZE = 14                 # Title bar text
HEADING_SIZE = 16               # Section headings
BODY_SIZE = 13                  # Body text
CAPTION_SIZE = 11               # Small labels

# -- Spacing ------------------------------------------------------------------

PADDING_SM = 8
PADDING_MD = 16
PADDING_LG = 24
BORDER_RADIUS = 8
TITLE_BAR_HEIGHT = 40
DRAWER_WIDTH = 360

# -- Button Styles ------------------------------------------------------------

BUTTON_STYLE = ft.ButtonStyle(
    bgcolor={
        ft.ControlState.DEFAULT: ACCENT,
        ft.ControlState.HOVERED: ACCENT_HOVER,
    },
    color=TEXT_PRIMARY,
    shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS),
    padding=ft.padding.symmetric(horizontal=PADDING_LG, vertical=PADDING_SM),
)

ICON_BUTTON_STYLE = ft.ButtonStyle(
    color={
        ft.ControlState.DEFAULT: TEXT_SECONDARY,
        ft.ControlState.HOVERED: TEXT_PRIMARY,
    },
    padding=ft.padding.all(PADDING_SM),
)
