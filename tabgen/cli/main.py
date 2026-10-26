"""Thin typer-based CLI layer for tabgen."""

import json
from typing import Optional

import typer
from rich.console import Console

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


if __name__ == "__main__":
    app()
