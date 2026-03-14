# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for YT Transcribe: desktop GUI + MCP server console exe."""

import os
import sys
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH)
BUILD_DIR = PROJECT_ROOT / "build"
FFMPEG_EXE = BUILD_DIR / "ffmpeg" / "ffmpeg.exe"

# Collect ffmpeg binary
ffmpeg_binaries = []
if FFMPEG_EXE.exists():
    ffmpeg_binaries = [(str(FFMPEG_EXE), ".")]

# Find flet package locations for runtime assets
import flet
import flet_desktop
flet_dir = Path(flet.__file__).parent
flet_desktop_dir = Path(flet_desktop.__file__).parent

# Shared hidden imports for the core library
_CORE_HIDDEN_IMPORTS = [
    "yt_transcribe",
    "yt_transcribe.models",
    "yt_transcribe.exceptions",
    "yt_transcribe.config",
    "yt_transcribe.download",
    "yt_transcribe.whisper_engine",
    "yt_transcribe.assemblyai_engine",
    "yt_transcribe.transcribe",
    "yt_transcribe.storage",
    "yt_transcribe.search",
    "yt_transcribe.jobs",
    "yt_transcribe.mcp_server",
    "yt_dlp",
    "yaml",
    "keyring",
    "keyring.backends",
    "assemblyai",
    "tenacity",
    "certifi",
    "charset_normalizer",
    "websockets",
]

# Modules to exclude from both builds (heavy ML deps download on first use)
_COMMON_EXCLUDES = [
    "torch",
    "torchaudio",
    "torchvision",
    "pytest",
    "mypy",
    "ruff",
]

# ---------------------------------------------------------------------------
# Analysis 1: Desktop GUI app
# ---------------------------------------------------------------------------
a_gui = Analysis(
    [str(PROJECT_ROOT / "ui" / "main.py")],
    pathex=[str(PROJECT_ROOT / "src"), str(PROJECT_ROOT)],
    binaries=ffmpeg_binaries,
    datas=[
        (str(flet_dir), "flet"),
        (str(flet_desktop_dir), "flet_desktop"),
        (str(PROJECT_ROOT / "assets" / "icon.png"), "assets"),
    ],
    hiddenimports=[
        *_CORE_HIDDEN_IMPORTS,
        # UI modules
        "ui",
        "ui.main",
        "ui.state",
        "ui.theme",
        "ui.components",
        "ui.components.title_bar",
        "ui.components.url_input",
        "ui.components.job_row",
        "ui.components.settings_drawer",
        "ui.pages",
        "ui.pages.main_page",
        # Flet dependencies
        "flet",
        "flet_runtime",
        "flet_desktop",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_COMMON_EXCLUDES,
    noarchive=False,
    optimize=0,
)

pyz_gui = PYZ(a_gui.pure, a_gui.zipped_data, cipher=block_cipher)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name="YT Transcribe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "assets" / "icon.ico"),
)

# ---------------------------------------------------------------------------
# Analysis 2: MCP server (console exe, stdio transport)
# ---------------------------------------------------------------------------
a_mcp = Analysis(
    [str(PROJECT_ROOT / "src" / "yt_transcribe" / "mcp_server.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=ffmpeg_binaries,
    datas=[],
    hiddenimports=[
        *_CORE_HIDDEN_IMPORTS,
        # MCP SDK modules
        "mcp",
        "mcp.server",
        "mcp.server.stdio",
        "mcp.types",
        "anyio",
        "anyio._backends",
        "anyio._backends._asyncio",
        "httpx",
        "httpcore",
        "sniffio",
        "h11",
        "pydantic",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        *_COMMON_EXCLUDES,
        # MCP server doesn't need Flet
        "flet",
        "flet_runtime",
        "flet_desktop",
    ],
    noarchive=False,
    optimize=0,
)

pyz_mcp = PYZ(a_mcp.pure, a_mcp.zipped_data, cipher=block_cipher)

exe_mcp = EXE(
    pyz_mcp,
    a_mcp.scripts,
    [],
    exclude_binaries=True,
    name="yt-transcribe-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console exe for stdio MCP transport
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ---------------------------------------------------------------------------
# Single COLLECT: both exes share one output folder
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe_gui,
    a_gui.binaries,
    a_gui.datas,
    exe_mcp,
    a_mcp.binaries,
    a_mcp.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YT Transcribe",
)
