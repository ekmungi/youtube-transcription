"""Dark theme constants matching ai-meeting-notes warm dark palette."""

from __future__ import annotations

import flet as ft


# -- Colors (ai-meeting-notes palette) ----------------------------------------

BG_PRIMARY = "#262624"          # Main background
BG_SURFACE = "#2E2D2B"         # Cards, panels
BG_ELEVATED = "#383632"        # Elevated surfaces, hover states
ACCENT = "#E03A3A"             # Primary accent (red)
ACCENT_HOVER = "#C42F2F"       # Accent hover state
ACCENT_BLUE = "#4A90D9"        # Secondary accent (links, focus)
ACCENT_GREEN = "#3AB56B"       # Success states
ACCENT_AMBER = "#D4A017"       # Warning states
TEXT_PRIMARY = "#E8E8E0"       # Main text
TEXT_SECONDARY = "#909088"     # Muted text
TEXT_MUTED = "#606058"         # Disabled / placeholder text
BORDER = "#3A3A38"             # Borders and dividers
ERROR = "#E03A3A"              # Error states (same as accent)
SUCCESS = "#3AB56B"            # Completed states
WARNING = "#D4A017"            # Warning states

# -- Typography ---------------------------------------------------------------

FONT_FAMILY = "Fira Sans"
TITLE_SIZE = 17                # Title bar text
HEADING_SIZE = 15              # Section headings (uppercase style)
BODY_SIZE = 15                 # Body text
CAPTION_SIZE = 13              # Small labels

# -- Spacing ------------------------------------------------------------------

PADDING_SM = 8
PADDING_MD = 16
PADDING_LG = 24
BORDER_RADIUS = 6
TITLE_BAR_HEIGHT = 40
DRAWER_WIDTH = 420

# -- Button Styles ------------------------------------------------------------

BUTTON_STYLE = ft.ButtonStyle(
    bgcolor={
        ft.ControlState.DEFAULT: ACCENT,
        ft.ControlState.HOVERED: ACCENT_HOVER,
    },
    color="#FFFFFF",
    shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS),
    padding=ft.padding.symmetric(horizontal=PADDING_LG, vertical=PADDING_SM),
)

BUTTON_STYLE_SECONDARY = ft.ButtonStyle(
    bgcolor={
        ft.ControlState.DEFAULT: BG_SURFACE,
        ft.ControlState.HOVERED: BG_ELEVATED,
    },
    color=TEXT_PRIMARY,
    side={
        ft.ControlState.DEFAULT: ft.BorderSide(1, BORDER),
    },
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
