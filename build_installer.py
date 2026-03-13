"""Build script for YT Transcribe Windows installer.

Downloads ffmpeg, runs PyInstaller, and prepares files for Inno Setup.
Usage: uv run python build_installer.py
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
FFMPEG_DIR = BUILD_DIR / "ffmpeg"
FFMPEG_EXE = FFMPEG_DIR / "ffmpeg.exe"

# ffmpeg release URL (essentials build from gyan.dev)
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def download_ffmpeg() -> None:
    """Download ffmpeg.exe if not already present."""
    if FFMPEG_EXE.exists():
        print(f"ffmpeg already at {FFMPEG_EXE}")
        return

    FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading ffmpeg from {FFMPEG_URL}...")

    response = urllib.request.urlopen(FFMPEG_URL)
    zip_data = io.BytesIO(response.read())

    with zipfile.ZipFile(zip_data) as zf:
        # Find ffmpeg.exe inside the zip (nested in a versioned folder)
        for name in zf.namelist():
            if name.endswith("bin/ffmpeg.exe"):
                print(f"Extracting {name}...")
                data = zf.read(name)
                FFMPEG_EXE.write_bytes(data)
                break

    if not FFMPEG_EXE.exists():
        print("ERROR: Could not find ffmpeg.exe in zip")
        sys.exit(1)

    print(f"ffmpeg saved to {FFMPEG_EXE}")


def run_pyinstaller() -> None:
    """Run PyInstaller with the spec file."""
    spec_file = PROJECT_ROOT / "yt_transcribe.spec"
    if not spec_file.exists():
        print(f"ERROR: {spec_file} not found")
        sys.exit(1)

    print("Running PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_file), "--noconfirm"],
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print("ERROR: PyInstaller failed")
        sys.exit(1)

    print("PyInstaller complete")


def verify_build() -> None:
    """Check that the output exe exists."""
    exe_path = DIST_DIR / "YT Transcribe" / "YT Transcribe.exe"
    if not exe_path.exists():
        print(f"ERROR: Expected output not found at {exe_path}")
        sys.exit(1)

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"Build verified: {exe_path} ({size_mb:.1f} MB)")


def main() -> None:
    """Run the full build pipeline."""
    print("=" * 60)
    print("YT Transcribe - Build Installer")
    print("=" * 60)

    download_ffmpeg()
    run_pyinstaller()
    verify_build()

    print()
    print("=" * 60)
    print("Build complete!")
    print(f"Output: {DIST_DIR / 'YT Transcribe'}")
    print()
    print("Next steps:")
    print("  1. Test: dist/YT Transcribe/YT Transcribe.exe")
    print("  2. Install Inno Setup: https://jrsoftware.org/isinfo.php")
    print("  3. Compile: iscc installer.iss")
    print("=" * 60)


if __name__ == "__main__":
    main()
