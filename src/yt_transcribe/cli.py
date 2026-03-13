"""CLI entry point built with click + rich. Thin wrapper over core library."""

from __future__ import annotations

from dataclasses import replace

import click
from rich.console import Console
from rich.table import Table

from yt_transcribe import config as config_mod
from yt_transcribe import download, jobs, search, storage, transcribe
from yt_transcribe.config import load_config
from yt_transcribe.jobs import JOBS_DB_PATH
from yt_transcribe.models import TranscriptionStrategy, WhisperModel

console = Console()

# Valid config keys and their types for `config set`
_CONFIG_KEYS: dict[str, type] = {
    "obsidian_vault_path": str,
    "transcript_folder": str,
    "transcription_strategy": str,
    "whisper_model": str,
    "async_threshold_seconds": int,
    "parallel_enabled": bool,
}


def _get_db():
    """Open the jobs database connection.

    Returns:
        sqlite3.Connection to the jobs database.
    """
    return jobs.get_or_create_db(JOBS_DB_PATH)


@click.group()
def cli() -> None:
    """YouTube transcript extractor -- yt-transcribe."""


@cli.command()
@click.argument("url")
def video(url: str) -> None:
    """Transcribe a single YouTube video."""
    cfg = load_config()
    video_info = download.get_video_info(url)

    existing = storage.find_existing(cfg, video_info.video_id)
    if existing is not None:
        console.print(f"[green]Already exists (cached):[/green] {video_info.title}")
        return

    console.print(f"Transcribing: {video_info.title}...")
    transcript = transcribe.transcribe_video(video_info, cfg)
    storage.save_transcript(cfg, transcript)
    console.print(f"[green]Saved:[/green] {video_info.title}")


@cli.command()
@click.argument("url")
def playlist(url: str) -> None:
    """Transcribe all videos in a YouTube playlist."""
    cfg = load_config()
    videos = download.get_playlist_info(url)
    console.print(f"Found {len(videos)} videos in playlist")

    for i, vid in enumerate(videos, 1):
        existing = storage.find_existing(cfg, vid.video_id)
        if existing is not None:
            console.print(f"  [{i}/{len(videos)}] {vid.title} (cached)")
            continue

        console.print(f"  [{i}/{len(videos)}] Transcribing: {vid.title}...")
        transcript = transcribe.transcribe_video(vid, cfg)
        storage.save_transcript(cfg, transcript)
        console.print(f"  [{i}/{len(videos)}] [green]Saved:[/green] {vid.title}")


@cli.command("list")
@click.option("--folder", default=None, help="Filter by subfolder name")
def list_cmd(folder: str | None) -> None:
    """List saved transcripts in the Obsidian vault."""
    cfg = load_config()
    entries = search.list_transcripts(cfg, folder=folder)

    if not entries:
        console.print("No transcripts found.")
        return

    table = Table(title="Saved Transcripts")
    table.add_column("Title", style="cyan")
    table.add_column("Channel")
    table.add_column("ID", style="dim")
    for entry in entries:
        table.add_row(entry.title, entry.channel, entry.video_id)
    console.print(table)


@cli.command("search")
@click.argument("query")
def search_cmd(query: str) -> None:
    """Search across saved transcripts."""
    cfg = load_config()
    matches = search.search_transcripts(cfg, query)

    if not matches:
        console.print("No matches found.")
        return

    for match in matches:
        console.print(f"[cyan]{match.title}[/cyan]")
        console.print(f"  {match.snippet}")
        console.print()


@cli.command("jobs")
def jobs_cmd() -> None:
    """Show active and recent transcription jobs."""
    conn = _get_db()
    all_jobs = jobs.list_jobs(conn)
    conn.close()

    if not all_jobs:
        console.print("No jobs found.")
        return

    table = Table(title="Jobs")
    table.add_column("Job ID", style="cyan")
    table.add_column("Status")
    table.add_column("Progress")
    table.add_column("Error", style="red")
    for job in all_jobs:
        table.add_row(
            job["job_id"],
            job["status"],
            f"{job['completed_count']}/{job['video_count']}",
            job["error"] or "",
        )
    console.print(table)


@cli.group(invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show or update configuration."""
    if ctx.invoked_subcommand is not None:
        return

    cfg = load_config()
    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_row("obsidian_vault_path", cfg.obsidian_vault_path)
    table.add_row("transcript_folder", cfg.transcript_folder)
    table.add_row("transcription_strategy", cfg.transcription_strategy.value)
    table.add_row("whisper_model", cfg.whisper_model.value)
    table.add_row("async_threshold_seconds", str(cfg.async_threshold_seconds))
    table.add_row("parallel_enabled", str(cfg.parallel_enabled))
    console.print(table)


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value. Usage: config set <key> <value>."""
    if key not in _CONFIG_KEYS:
        console.print(f"[red]Unknown config key:[/red] {key}")
        raise SystemExit(1)

    cfg = load_config()

    # Convert value to the correct type
    if key == "transcription_strategy":
        new_val = TranscriptionStrategy(value)
    elif key == "whisper_model":
        new_val = WhisperModel(value)
    elif key == "async_threshold_seconds":
        new_val = int(value)
    elif key == "parallel_enabled":
        new_val = value.lower() in ("true", "1", "yes")
    else:
        new_val = value

    updated = replace(cfg, **{key: new_val})
    config_mod.save_config(updated)
    console.print(f"[green]Set {key} = {value}[/green]")


def main() -> None:
    """Entry point for yt-transcribe CLI."""
    cli()


if __name__ == "__main__":
    main()
