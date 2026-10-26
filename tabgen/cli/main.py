"""Thin typer-based CLI layer for tabgen."""

import json
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from tabgen import __version__
from tabgen.core import doctor as doctor_core

app = typer.Typer(
    name="tabgen",
    help="Generate guitar tablature from audio files.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"tabgen {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the tabgen version and exit.",
    ),
) -> None:
    """tabgen command-line interface."""


@app.command()
def doctor(
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print the raw check results as JSON.",
    ),
) -> None:
    """Check that the environment can run tabgen (ffmpeg, Python, CUDA, disk)."""
    report = doctor_core.run_checks()

    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        for check in report.checks:
            mark = "[green]✓[/green]" if check.ok else "[red]✗[/red]"
            console.print(f"{mark} {check.name}: {check.detail}")
        if report.ok:
            console.print("[green]All essential checks passed.[/green]")
        else:
            console.print("[red]Some essential checks failed.[/red]")

    raise typer.Exit(0 if report.ok else 1)


@app.command()
def separate(
    audio: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help="Audio file to separate (mp3, flac, wav, ...).",
    ),
    device: Optional[str] = typer.Option(
        None,
        "--device",
        help="Device for Demucs: cuda or cpu (default: autodetect).",
    ),
) -> None:
    """Separate the audio into guitar/bass/drums/vocals/other stems."""
    from tabgen.core.separation import demucs as demucs_core

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Separating stems", total=100.0)

        def on_progress(stage: str, pct: float) -> None:
            progress.update(task, completed=pct)

        try:
            result, cache_hit = demucs_core.separate(
                audio, device=device, on_progress=on_progress
            )
        except demucs_core.SeparationError as err:
            progress.stop()
            console.print(f"[red]Separation failed:[/red] {err}")
            raise typer.Exit(1) from err

    if cache_hit:
        console.print("[yellow]cache hit[/yellow]: stems reused, Demucs skipped.")
    console.print(f"Stems written to [bold]{audio.parent / 'stems'}[/bold]:")
    for name, path in sorted(result.stems.items()):
        console.print(f"  {name}: {path}")


@app.command()
def transcribe(
    audio: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help="Audio file to transcribe (mp3, flac, wav, ...).",
    ),
    instruments: str = typer.Option(
        "guitar,bass",
        "--instruments",
        help="Comma-separated instruments to transcribe (guitar, bass).",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        file_okay=False,
        help="Directory for the .mid files (default: next to the input).",
    ),
    device: Optional[str] = typer.Option(
        None,
        "--device",
        help="Device for Demucs: cuda or cpu (default: autodetect).",
    ),
) -> None:
    """Transcribe the audio into one MIDI file per instrument."""
    from tabgen.core.pipeline import PipelineError, run_transcription
    from tabgen.core.separation.demucs import SeparationError
    from tabgen.core.transcription.basic_pitch import TranscriptionError

    wanted = tuple(name.strip() for name in instruments.split(",") if name.strip())

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        tasks: dict[str, Any] = {}

        def on_progress(stage: str, pct: float) -> None:
            if stage not in tasks:
                tasks[stage] = progress.add_task(stage, total=100.0)
            progress.update(tasks[stage], completed=pct)

        try:
            summary = run_transcription(
                audio,
                instruments=wanted,
                device=device,
                output_dir=output_dir,
                on_progress=on_progress,
            )
        except (PipelineError, SeparationError, TranscriptionError) as err:
            progress.stop()
            console.print(f"[red]Transcription failed:[/red] {err}")
            raise typer.Exit(1) from err

    if summary.separation_cache_hit:
        console.print("[yellow]cache hit[/yellow]: stems reused, Demucs skipped.")
    console.print("MIDI files written:")
    for item in summary.instruments:
        hit = " [yellow](cache hit)[/yellow]" if item.cache_hit else ""
        console.print(
            f"  {item.instrument}: {item.note_count} notes -> "
            f"[bold]{item.midi_path}[/bold]{hit}"
        )


if __name__ == "__main__":
    app()
