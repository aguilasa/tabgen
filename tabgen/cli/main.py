"""Thin typer-based CLI layer for tabgen."""

import json
from pathlib import Path
from typing import Optional

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


if __name__ == "__main__":
    app()
