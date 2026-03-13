# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for YT Transcribe desktop app."""

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

a = Analysis(
    [str(PROJECT_ROOT / "ui" / "main.py")],
    pathex=[str(PROJECT_ROOT / "src"), str(PROJECT_ROOT)],
    binaries=ffmpeg_binaries,
    datas=[
        # Flet runtime assets
        (str(flet_dir), "flet"),
        # Flet desktop runtime (Flutter engine, DLLs, flet.exe)
        (str(flet_desktop_dir), "flet_desktop"),
    ],
    hiddenimports=[
        # Core library modules
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
        # Dependencies that PyInstaller may miss
        "flet",
        "flet_runtime",
        "flet_desktop",
        "yt_dlp",
        "yaml",
        "keyring",
        "keyring.backends",
        "assemblyai",
        "tenacity",
        "certifi",
        "charset_normalizer",
        "websockets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy ML deps -- Whisper downloads on first use
        "torch",
        "torchaudio",
        "torchvision",
        # Exclude test/dev tools
        "pytest",
        "mypy",
        "ruff",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
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
    # icon=str(PROJECT_ROOT / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YT Transcribe",
)
