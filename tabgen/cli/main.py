"""Thin typer-based CLI layer for tabgen."""

from typing import Optional

import typer
from rich.console import Console

from tabgen import __version__

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


if __name__ == "__main__":
    app()
