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
    guitar_type: Optional[str] = typer.Option(
        None,
        "--guitar-type",
        help="Guitar type: electric, nylon or steel; sets the General MIDI "
        "program of the guitar file (default: electric, program 27).",
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
                guitar_type=guitar_type.strip().lower() if guitar_type else None,
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


@app.command()
def analyze(
    audio: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help="Audio file to analyze (mp3, flac, wav, ...).",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        dir_okay=False,
        help="Path for the analysis JSON (default: <input>.analysis.json "
        "next to the input).",
    ),
    device: Optional[str] = typer.Option(
        None,
        "--device",
        help="Device for Demucs: cuda or cpu (default: autodetect).",
    ),
) -> None:
    """Analyze the audio: key, tempo/beats and chord sequence."""
    from tabgen.core.analysis.beats import BeatAnalysisError
    from tabgen.core.analysis.harmony import HarmonyError
    from tabgen.core.pipeline import PipelineError, run_analysis
    from tabgen.core.separation.demucs import SeparationError

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
            summary = run_analysis(audio, device=device, on_progress=on_progress)
        except (
            PipelineError,
            SeparationError,
            BeatAnalysisError,
            HarmonyError,
        ) as err:
            progress.stop()
            console.print(f"[red]Analysis failed:[/red] {err}")
            raise typer.Exit(1) from err

    result = summary.result
    out_path = (
        output if output is not None else audio.parent / f"{audio.stem}.analysis.json"
    )
    out_path.write_text(result.to_json(), encoding="utf-8")

    if summary.analysis_cache_hit:
        console.print("[yellow]cache hit[/yellow]: analysis reused, madmom skipped.")
    elif summary.separation_cache_hit:
        console.print("[yellow]cache hit[/yellow]: stems reused, Demucs skipped.")
    console.print(
        f"Key: [bold]{result.key or 'unknown'}[/bold] "
        f"(confidence {result.key_confidence:.2f})"
    )
    console.print(
        f"Tempo: [bold]{result.tempo_bpm:.1f} BPM[/bold] "
        f"({len(result.beat_times)} beats, "
        f"{len(result.downbeat_times)} downbeats)"
    )
    if result.chords:
        console.print("Chords:")
        for segment in result.chords:
            console.print(
                f"  {segment.start_s:7.2f}s - {segment.end_s:7.2f}s  {segment.label}"
            )
    else:
        console.print("Chords: none detected.")
    console.print(f"Analysis written to [bold]{out_path}[/bold]")


@app.command()
def export(
    audio: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help="Audio file to turn into tablature (mp3, flac, wav, ...).",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        dir_okay=False,
        help="Output file (default: <input>.gp5 next to the input). The "
        "suffix picks the format: .gp5, .musicxml/.xml or .txt (ASCII tab).",
    ),
    fmt: Optional[str] = typer.Option(
        None,
        "--format",
        help="Force the format: gp5, musicxml or ascii (default: from the "
        "output suffix).",
    ),
    instruments: str = typer.Option(
        "guitar,bass",
        "--instruments",
        help="Comma-separated instruments to include (guitar, bass).",
    ),
    tuning: Optional[str] = typer.Option(
        None,
        "--tuning",
        help="Guitar tuning: a preset (standard, drop-d, half-step-down, "
        "d-standard) or notes low-to-high, e.g. D2,A2,D3,G3,B3,E4.",
    ),
    bass_tuning: Optional[str] = typer.Option(
        None,
        "--bass-tuning",
        help="Bass tuning: a preset (standard, drop-d, half-step-down, "
        "five-string = B0,E1,A1,D2,G2) or notes low-to-high, e.g. E1,A1,D2,G2.",
    ),
    guitar_type: str = typer.Option(
        "electric",
        "--guitar-type",
        help="Guitar type: electric, nylon or steel. Sets the General MIDI "
        "program of the guitar track (27 clean electric, 24 nylon, 25 steel) "
        "and the highest fret used (24, 19, 20).",
    ),
    capo: int = typer.Option(
        0,
        "--capo",
        min=0,
        max=12,
        help="Guitar capo fret (frets in the tab are relative to it).",
    ),
    device: Optional[str] = typer.Option(
        None,
        "--device",
        help="Device for Demucs: cuda or cpu (default: autodetect).",
    ),
    techniques: bool = typer.Option(
        True,
        "--techniques/--no-techniques",
        help="Detect and write bends, slides, hammer-ons and pull-offs "
        "(--no-techniques writes plain picked notes only).",
    ),
) -> None:
    """Generate tablature (Guitar Pro 5, MusicXML or ASCII) from the audio."""
    from tabgen.core.analysis.beats import BeatAnalysisError
    from tabgen.core.analysis.harmony import HarmonyError
    from tabgen.core.models import DEFAULT_GUITAR_TYPE, GUITAR_TYPES
    from tabgen.core.pipeline import (
        PipelineError,
        resolve_export_format,
        resolve_tuning,
        run_tablature,
    )
    from tabgen.core.separation.demucs import SeparationError
    from tabgen.core.transcription.basic_pitch import TranscriptionError

    wanted = tuple(name.strip() for name in instruments.split(",") if name.strip())
    try:
        out_path = (
            output if output is not None else audio.parent / f"{audio.stem}.gp5"
        )
        out_format = resolve_export_format(out_path, fmt)
        guitar_type = guitar_type.strip().lower()
        if guitar_type not in GUITAR_TYPES:
            raise PipelineError(
                f"unknown guitar type {guitar_type!r}; choose one of "
                f"{', '.join(GUITAR_TYPES)}"
            )
        tunings = {}
        if "guitar" in wanted:
            tunings["guitar"] = resolve_tuning(tuning, "guitar")
        if "bass" in wanted:
            tunings["bass"] = resolve_tuning(bass_tuning, "bass")
    except PipelineError as err:
        console.print(f"[red]Invalid option:[/red] {err}")
        raise typer.Exit(2) from err

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
            summary = run_tablature(
                audio,
                output_path=out_path,
                fmt=out_format,
                instruments=wanted,
                tunings=tunings,
                capos={"guitar": capo},
                device=device,
                on_progress=on_progress,
                techniques=techniques,
                guitar_type=guitar_type,
            )
        except (
            PipelineError,
            SeparationError,
            TranscriptionError,
            BeatAnalysisError,
            HarmonyError,
        ) as err:
            progress.stop()
            console.print(f"[red]Export failed:[/red] {err}")
            raise typer.Exit(1) from err

    if summary.cache_hit:
        console.print(
            "[yellow]cache hit[/yellow]: tablature reused, Demucs, Basic Pitch, "
            "madmom and fretting skipped."
        )
    check = summary.key_check
    switched = " (switched from the analysis key by the note histogram)" if (
        check.get("switched")
    ) else ""
    console.print(f"Key: [bold]{check.get('key') or 'unknown'}[/bold]{switched}")
    for score in summary.scores:
        dropped = summary.unassigned.get(score.instrument, 0)
        extra = f", {dropped} unplayable note(s) left out" if dropped else ""
        if techniques:
            marked = sum(1 for event in score.events if event.technique is not None)
            extra += f", {marked} technique(s)"
        shown_type = score.instrument_type not in ("", DEFAULT_GUITAR_TYPE)
        kind = f" ({score.instrument_type})" if shown_type else ""
        console.print(
            f"  {score.instrument}{kind}: {len(score.events)} notes, "
            f"tuning {score.tuning_midi}, capo {score.capo_fret}{extra}"
        )
    console.print(
        f"Tablature ({summary.format}) written to [bold]{summary.output_path}[/bold]"
    )


if __name__ == "__main__":
    app()
