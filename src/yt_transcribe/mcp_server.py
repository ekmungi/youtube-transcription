"""MCP server exposing YouTube transcript tools via stdio transport.

5 tools: get_transcript, get_playlist_transcripts, list_transcripts,
search_transcripts, check_job_status. Thin wrapper over the core library.

All blocking I/O (yt-dlp, transcription, file ops) is wrapped in
asyncio.to_thread() to avoid blocking the MCP event loop.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from dataclasses import replace

from yt_transcribe import download, jobs, search, storage, transcribe
from yt_transcribe.config import load_config
from yt_transcribe.download import extract_video_data
from yt_transcribe.jobs import JOBS_DB_PATH
from yt_transcribe.models import TranscriptionStrategy, WhisperModel

# Rough estimate: 1s processing per 1s of audio
_SYNC_ESTIMATE_RATIO = 1.0

# Pattern to extract video ID from common YouTube URL formats
_VIDEO_ID_PATTERN = re.compile(
    r"(?:v=|youtu\.be/|/embed/|/v/|/shorts/)([a-zA-Z0-9_-]{11})"
)


def _extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from a URL.

    Args:
        url: YouTube video URL in any common format.

    Returns:
        11-character video ID, or None if not found.
    """
    match = _VIDEO_ID_PATTERN.search(url)
    return match.group(1) if match else None


def _get_db():
    """Open the jobs database connection.

    Returns:
        sqlite3.Connection to the jobs database.
    """
    return jobs.get_or_create_db(JOBS_DB_PATH)


def _apply_overrides(
    strategy: str | None = None,
    whisper_model: str | None = None,
) -> "Config":
    """Load config and apply optional per-call overrides.

    Args:
        strategy: Override transcription strategy (auto, captions, cloud, local).
        whisper_model: Override whisper model size (tiny, base, small, medium).

    Returns:
        Config with overrides applied.
    """
    from yt_transcribe.models import Config

    config = load_config()
    if strategy:
        config = replace(config, transcription_strategy=TranscriptionStrategy(strategy))
    if whisper_model:
        config = replace(config, whisper_model=WhisperModel(whisper_model))
    return config


def _sync_get_transcript(
    video_url: str,
    strategy: str | None = None,
    whisper_model: str | None = None,
) -> dict[str, Any]:
    """Synchronous implementation of get_transcript (runs in thread pool).

    Args:
        video_url: YouTube video URL.
        strategy: Override transcription strategy.
        whisper_model: Override whisper model size.

    Returns:
        Dict with transcript text or job_id for async processing.
    """
    config = _apply_overrides(strategy, whisper_model)

    # Cache-first: check Obsidian vault by video_id
    video_id = _extract_video_id(video_url)
    if video_id:
        existing_path = storage.find_existing(config, video_id)
        if existing_path is not None:
            return {"video_id": video_id, "source": "cache", "path": str(existing_path)}

    # Single yt-dlp call: metadata + captions + audio URL
    video_data = extract_video_data(video_url)
    video = video_data.video_info
    estimated_seconds = video.duration_seconds * _SYNC_ESTIMATE_RATIO

    if estimated_seconds > config.async_threshold_seconds:
        conn = _get_db()
        job_id = jobs.create_job(conn, (video,))
        conn.close()
        return {
            "job_id": job_id,
            "status": "async",
            "estimated_seconds": estimated_seconds,
        }

    # Use optimized fast path with pre-fetched data
    transcript_result = transcribe.transcribe_video_fast(video_data, config)
    storage.save_transcript(config, transcript_result)
    return {
        "text": transcript_result.text,
        "source": "transcribed",
        "title": video.title,
    }


def _sync_get_playlist_transcripts(
    playlist_url: str,
    strategy: str | None = None,
    whisper_model: str | None = None,
) -> dict[str, Any]:
    """Synchronous implementation of get_playlist_transcripts (runs in thread pool).

    Args:
        playlist_url: YouTube playlist URL.
        strategy: Override transcription strategy.
        whisper_model: Override whisper model size.

    Returns:
        Dict with transcript results or job_id for async processing.
    """
    config = _apply_overrides(strategy, whisper_model)
    videos = download.get_playlist_info(playlist_url)
    total_estimate = sum(v.duration_seconds * _SYNC_ESTIMATE_RATIO for v in videos)

    if total_estimate > config.async_threshold_seconds:
        conn = _get_db()
        job_id = jobs.create_job(conn, videos)
        conn.close()
        return {"job_id": job_id, "status": "async", "video_count": len(videos)}

    results: list[dict[str, str]] = []
    for video in videos:
        existing = storage.find_existing(config, video.video_id)
        if existing is not None:
            results.append({"title": video.title, "source": "cache"})
            continue
        # Use optimized single-call pipeline per video
        video_data = extract_video_data(video.url)
        transcript_result = transcribe.transcribe_video_fast(video_data, config)
        storage.save_transcript(config, transcript_result)
        results.append({
            "title": video.title,
            "text": transcript_result.text,
            "source": "transcribed",
        })

    return {"transcripts": results}


def _sync_list_transcripts(folder: str | None = None) -> dict[str, Any]:
    """Synchronous implementation of list_transcripts (runs in thread pool).

    Args:
        folder: Optional subfolder name to filter.

    Returns:
        Dict with list of transcript metadata entries.
    """
    config = load_config()
    entries = search.list_transcripts(config, folder=folder)
    return {
        "transcripts": [
            {
                "title": e.title,
                "channel": e.channel,
                "video_id": e.video_id,
                "path": str(e.file_path),
            }
            for e in entries
        ]
    }


def _sync_search_transcripts(query: str) -> dict[str, Any]:
    """Synchronous implementation of search_transcripts (runs in thread pool).

    Args:
        query: Search string (case-insensitive).

    Returns:
        Dict with list of matching snippets.
    """
    config = load_config()
    matches = search.search_transcripts(config, query)
    return {
        "matches": [
            {
                "title": m.title,
                "channel": m.channel,
                "snippet": m.snippet,
                "path": str(m.file_path),
            }
            for m in matches
        ]
    }


def _sync_check_job_status(job_id: str) -> dict[str, Any]:
    """Synchronous implementation of check_job_status (runs in thread pool).

    Args:
        job_id: Unique job identifier.

    Returns:
        Dict with job status fields, or error if not found.
    """
    conn = _get_db()
    job = jobs.get_job(conn, job_id)
    conn.close()

    if job is None:
        return {"error": f"Job '{job_id}' not found"}

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "video_count": job["video_count"],
        "completed_count": job["completed_count"],
        "error": job["error"],
    }


# -- Async wrappers (run blocking I/O in thread pool) -----------------------

async def handle_get_transcript(
    video_url: str,
    strategy: str | None = None,
    whisper_model: str | None = None,
) -> dict[str, Any]:
    """Transcribe a single video. Non-blocking async wrapper."""
    return await asyncio.to_thread(
        _sync_get_transcript, video_url, strategy, whisper_model,
    )


async def handle_get_playlist_transcripts(
    playlist_url: str,
    strategy: str | None = None,
    whisper_model: str | None = None,
) -> dict[str, Any]:
    """Transcribe all videos in a playlist. Non-blocking async wrapper."""
    return await asyncio.to_thread(
        _sync_get_playlist_transcripts, playlist_url, strategy, whisper_model,
    )


async def handle_list_transcripts(folder: str | None = None) -> dict[str, Any]:
    """List saved transcripts. Non-blocking async wrapper."""
    return await asyncio.to_thread(_sync_list_transcripts, folder)


async def handle_search_transcripts(query: str) -> dict[str, Any]:
    """Search transcripts. Non-blocking async wrapper."""
    return await asyncio.to_thread(_sync_search_transcripts, query)


async def handle_check_job_status(job_id: str) -> dict[str, Any]:
    """Check job status. Non-blocking async wrapper."""
    return await asyncio.to_thread(_sync_check_job_status, job_id)


# -- MCP server wiring -------------------------------------------------------

_TOOLS = (
    Tool(
        name="get_transcript",
        description=(
            "Transcribe a YouTube video and save to Obsidian vault. "
            "IMPORTANT: Always ask the user which strategy to use before calling this tool. "
            "Options: 'captions' (free, instant, uses YouTube's own subtitles), "
            "'cloud' (fast, uses AssemblyAI, requires API key), "
            "'local' (free, slow, uses Whisper on CPU), "
            "'auto' (tries captions first, then cloud, then local)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "video_url": {"type": "string", "description": "YouTube video URL"},
                "strategy": {
                    "type": "string",
                    "description": "Transcription strategy. Ask the user which to use: captions (free/instant), cloud (fast/paid), local (free/slow), auto (cascading fallback)",
                    "enum": ["auto", "captions", "cloud", "local"],
                },
                "whisper_model": {
                    "type": "string",
                    "description": "Whisper model size (only for local strategy): tiny, base, small, medium",
                    "enum": ["tiny", "base", "small", "medium"],
                },
            },
            "required": ["video_url", "strategy"],
        },
    ),
    Tool(
        name="get_playlist_transcripts",
        description=(
            "Transcribe all videos in a YouTube playlist. "
            "IMPORTANT: Always ask the user which strategy to use before calling this tool. "
            "Options: 'captions', 'cloud', 'local', 'auto'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "playlist_url": {"type": "string", "description": "YouTube playlist URL"},
                "strategy": {
                    "type": "string",
                    "description": "Transcription strategy. Ask the user which to use: captions (free/instant), cloud (fast/paid), local (free/slow), auto (cascading fallback)",
                    "enum": ["auto", "captions", "cloud", "local"],
                },
                "whisper_model": {
                    "type": "string",
                    "description": "Whisper model size (only for local strategy): tiny, base, small, medium",
                    "enum": ["tiny", "base", "small", "medium"],
                },
            },
            "required": ["playlist_url", "strategy"],
        },
    ),
    Tool(
        name="list_transcripts",
        description="List saved transcripts in the Obsidian vault",
        inputSchema={
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Optional subfolder filter"},
            },
        },
    ),
    Tool(
        name="search_transcripts",
        description="Full-text search across saved transcript content",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="check_job_status",
        description="Check progress of an async transcription job",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job identifier"},
            },
            "required": ["job_id"],
        },
    ),
)

_TOOL_HANDLERS: dict[str, Any] = {
    "get_transcript": lambda args: handle_get_transcript(
        args["video_url"], args.get("strategy"), args.get("whisper_model"),
    ),
    "get_playlist_transcripts": lambda args: handle_get_playlist_transcripts(
        args["playlist_url"], args.get("strategy"), args.get("whisper_model"),
    ),
    "list_transcripts": lambda args: handle_list_transcripts(args.get("folder")),
    "search_transcripts": lambda args: handle_search_transcripts(args["query"]),
    "check_job_status": lambda args: handle_check_job_status(args["job_id"]),
}


def _create_server() -> Server:
    """Create and configure the MCP server with all tool handlers.

    Returns:
        Configured MCP Server instance.
    """
    server = Server("yt-transcribe")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Return the list of available tools."""
        return list(_TOOLS)

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Dispatch a tool call to the appropriate handler.

        Args:
            name: Tool name string.
            arguments: Tool arguments dict.

        Returns:
            List with single TextContent containing JSON result.
        """
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        result = await handler(arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return server


async def _watch_parent(interval: float = 5.0) -> None:
    """Exit if the parent process dies (e.g. Claude Code closes).

    Polls the parent PID periodically. When the parent is gone, forces exit
    so the server doesn't linger as an orphaned process on Windows.

    Args:
        interval: Seconds between parent process checks.
    """
    import os
    import signal

    parent_pid = os.getppid()
    while True:
        await asyncio.sleep(interval)
        try:
            # On Windows, os.kill with signal 0 checks if process exists
            os.kill(parent_pid, 0)
        except (OSError, ProcessLookupError):
            # Parent is gone, exit immediately
            os._exit(0)


async def _run_server() -> None:
    """Start the MCP server with stdio transport and parent watchdog."""
    server = _create_server()

    async with stdio_server() as (read_stream, write_stream):
        # Run server and parent watchdog concurrently
        server_task = asyncio.create_task(
            server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
        )
        watchdog_task = asyncio.create_task(_watch_parent())

        # When either finishes (server closes or parent dies), cancel the other
        done, pending = await asyncio.wait(
            [server_task, watchdog_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()


def main() -> None:
    """Entry point for yt-transcribe-server."""
    asyncio.run(_run_server())


if __name__ == "__main__":
    main()
