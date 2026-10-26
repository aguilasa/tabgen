"""Pipeline primitives and stage orchestration.

Holds the progress-reporting contract shared by every stage and
:func:`run_transcription`, which chains separation → per-instrument
transcription → MIDI export. Heavy stage modules are imported lazily so
importing this module stays cheap; the stage functions are injectable
for tests.

This module is pure core: no print/typer/rich.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol, Sequence

# Called as on_progress(stage, pct) with pct in [0.0, 100.0].
ProgressCallback = Callable[[str, float], None]


def null_progress(stage: str, pct: float) -> None:
    """A ProgressCallback that ignores every update."""


class PipelineError(RuntimeError):
    """Raised when the pipeline cannot orchestrate its stages."""


class _SeparateFn(Protocol):
    def __call__(
        self,
        input_path: Path,
        device: Optional[str] = None,
        on_progress: ProgressCallback = null_progress,
    ): ...


class _TranscribeFn(Protocol):
    def __call__(
        self,
        input_path: Path,
        instrument: str = "guitar",
        on_progress: ProgressCallback = null_progress,
    ): ...


class _ExportFn(Protocol):
    def __call__(self, note_events, output_path: Path, bends=None) -> Path: ...


@dataclass
class InstrumentSummary:
    """Per-instrument outcome of :func:`run_transcription`."""

    instrument: str
    note_count: int
    midi_path: str
    cache_hit: bool  # transcription-stage cache hit for this instrument


@dataclass
class TranscriptionSummary:
    """Overall outcome of :func:`run_transcription`."""

    input_path: str
    separation_cache_hit: bool
    instruments: list[InstrumentSummary] = field(default_factory=list)


def _scoped_progress(
    on_progress: ProgressCallback, stage_name: str
) -> ProgressCallback:
    """Forward pct updates under a fixed stage name (e.g. per instrument)."""

    def callback(stage: str, pct: float) -> None:
        on_progress(stage_name, pct)

    return callback


def run_transcription(
    input_path: str | Path,
    instruments: Sequence[str] = ("guitar", "bass"),
    device: str | None = None,
    output_dir: str | Path | None = None,
    on_progress: ProgressCallback = null_progress,
    separate_fn: _SeparateFn | None = None,
    transcribe_fn: _TranscribeFn | None = None,
    export_fn: _ExportFn | None = None,
) -> TranscriptionSummary:
    """Separate the input, transcribe each instrument's stem, export MIDI.

    One ``.mid`` file is written per instrument, named
    ``<input-stem>.<instrument>.mid`` and placed next to the input (or in
    ``output_dir`` when given). Progress is reported per stage: the
    ``separation`` events come straight from the separation stage, then
    ``transcription:<instrument>`` and ``export:<instrument>`` follow for
    each instrument, every stage reaching 100.0.

    ``separate_fn`` / ``transcribe_fn`` / ``export_fn`` default to the real
    stages and exist for dependency injection in tests.
    """
    input_path = Path(input_path)
    if not instruments:
        raise PipelineError("no instruments requested")

    if separate_fn is None:
        from tabgen.core.separation.demucs import separate as separate_fn
    if transcribe_fn is None:
        from tabgen.core.transcription.basic_pitch import transcribe as transcribe_fn
    if export_fn is None:
        from tabgen.core.export.midi import export_midi as export_fn

    target_dir = Path(output_dir) if output_dir is not None else input_path.parent

    separation, separation_hit = separate_fn(
        input_path, device=device, on_progress=on_progress
    )

    missing = [name for name in instruments if name not in separation.stems]
    if missing:
        available = ", ".join(sorted(separation.stems)) or "none"
        raise PipelineError(
            f"no stem for instrument(s) {', '.join(missing)}; "
            f"available stems: {available}"
        )

    summary = TranscriptionSummary(
        input_path=str(input_path), separation_cache_hit=separation_hit
    )
    for instrument in instruments:
        stem_path = Path(separation.stems[instrument])
        result, transcription_hit = transcribe_fn(
            stem_path,
            instrument=instrument,
            on_progress=_scoped_progress(on_progress, f"transcription:{instrument}"),
        )

        export_stage = f"export:{instrument}"
        on_progress(export_stage, 0.0)
        midi_path = target_dir / f"{input_path.stem}.{instrument}.mid"
        export_fn(result.note_events, midi_path, bends=result.bends)
        on_progress(export_stage, 100.0)

        summary.instruments.append(
            InstrumentSummary(
                instrument=instrument,
                note_count=len(result.note_events.notes),
                midi_path=str(midi_path),
                cache_hit=transcription_hit,
            )
        )

    return summary
