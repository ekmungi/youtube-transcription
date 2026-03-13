# YT Transcribe

YouTube transcript extractor with 3-tier transcription cascade, MCP server integration, CLI, and desktop UI. Saves transcripts as markdown to an Obsidian vault.

## Features

- **3-tier transcription cascade**: YouTube captions (free, instant) -> AssemblyAI cloud (fast, API key required) -> Whisper local CPU (free, slow)
- **4 strategies**: `auto` (cascade), `captions` (YouTube only), `cloud` (AssemblyAI only), `local` (Whisper only)
- **3 interfaces**: Desktop GUI (Flet), CLI (click + rich), MCP server (stdio transport)
- **Obsidian vault output**: Saves transcripts as markdown with YAML frontmatter
- **Playlist support**: Expand and transcribe entire YouTube playlists
- **Deduplication**: Skips videos already transcribed in the vault
- **Full-text search**: Search across all saved transcripts

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- ffmpeg (auto-detected or configurable path)
- AssemblyAI API key (optional, for cloud transcription)

## Installation

### From source (development)

```bash
git clone https://github.com/ekmungi/youtube-transcription.git
cd youtube-transcription
uv sync
```

### Windows installer

Download `YT-Transcribe-Setup-0.2.0.exe` from [Releases](https://github.com/ekmungi/youtube-transcription/releases). The installer optionally registers the MCP server with Claude Code.

## Usage

### Desktop UI

```bash
uv run python -m ui.main
```

### CLI

```bash
# Transcribe a single video
uv run yt-transcribe video https://youtube.com/watch?v=VIDEO_ID

# Transcribe a playlist
uv run yt-transcribe playlist https://youtube.com/playlist?list=PLAYLIST_ID

# List saved transcripts
uv run yt-transcribe list

# Search transcripts
uv run yt-transcribe search "query"

# Configure settings
uv run yt-transcribe config --show
```

### MCP Server

The MCP server exposes 5 tools via stdio transport for use with Claude Code, Claude Desktop, or any MCP-compatible client.

**Claude Code (auto-discovery):** The `.mcp.json` in the project root is picked up automatically.

**Manual setup:** Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "yt-transcribe": {
      "command": "uv",
      "args": ["run", "yt-transcribe-server"],
      "cwd": "/path/to/youtube-transcription"
    }
  }
}
```

**Available tools:**

| Tool | Description |
|------|-------------|
| `get_transcript` | Transcribe a single YouTube video |
| `get_playlist_transcripts` | Transcribe all videos in a playlist |
| `list_transcripts` | List saved transcripts in the vault |
| `search_transcripts` | Full-text search across transcript content |
| `check_job_status` | Check progress of async transcription jobs |

## Configuration

Settings are stored in `~/.yt-transcribe/config.yaml`:

| Setting | Default | Description |
|---------|---------|-------------|
| `obsidian_vault_path` | `~/Documents/Obsidian` | Path to Obsidian vault |
| `transcript_folder` | `Transcripts` | Subfolder within the vault |
| `transcription_strategy` | `auto` | `auto`, `captions`, `cloud`, `local` |
| `whisper_model` | `base` | `tiny`, `base`, `small`, `medium` |
| `ffmpeg_location` | (auto-detect) | Path to ffmpeg binary |
| `parallel_enabled` | `false` | Enable parallel playlist processing |

AssemblyAI API key is stored securely via the OS keyring.

## Building

### PyInstaller (Windows exe)

```bash
# Place ffmpeg.exe in build/ffmpeg/ for bundling
uv run pyinstaller yt_transcribe.spec
```

Outputs `dist/YT Transcribe/` with both the GUI exe and MCP server console exe.

### Inno Setup installer

```bash
iscc installer.iss
```

Outputs `dist/YT-Transcribe-Setup-0.2.0.exe`.

## Architecture

```
src/yt_transcribe/       # Shared core library
  config.py              # YAML config + keyring for API keys
  models.py              # Immutable dataclasses (frozen=True)
  download.py            # yt-dlp: metadata, captions, audio download
  transcribe.py          # 3-tier orchestrator with cascade logic
  assemblyai_engine.py   # Cloud transcription engine
  whisper_engine.py      # Local CPU transcription engine
  storage.py             # Markdown output with frontmatter
  search.py              # Full-text search across vault
  jobs.py                # SQLite job queue for async processing
  mcp_server.py          # MCP server (5 tools, stdio transport)
  cli.py                 # CLI (click + rich)

ui/                      # Flet desktop application
  main.py                # App entry point and state wiring
  state.py               # Immutable app state management
  theme.py               # Centralized theme constants
  components/            # Reusable UI components
  pages/                 # Page layouts
```

## License

MIT
