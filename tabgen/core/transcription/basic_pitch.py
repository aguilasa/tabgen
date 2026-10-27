"""Transcription built on Spotify's Basic Pitch (ICASSP 2022 model).

The model runs through the ONNX backend (onnxruntime). On Linux +
Python 3.11 basic-pitch's wheel metadata would drag in TensorFlow,
which conflicts with the torch stack (it forces numpy<2), so
basic-pitch is installed without its dependency chain and onnxruntime
makes it pick the bundled ``nmp.onnx`` model (see pyproject.toml).

Per-instrument frequency profiles bound the model's output range: the
bass profile caps the range to the bass tessitura so low notes (e.g.
E1 = 41.2 Hz) are not folded up an octave.

Results are cached through :class:`StageCache` keyed on stage + input
hash + model version + instrument, so a second call for the same stem
and instrument skips the model entirely.

This module is pure core: no stdout/typer/rich. Progress is reported
through the :data:`~tabgen.core.pipeline.ProgressCallback` contract.
"""

from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from tabgen.core.cache import StageCache
from tabgen.core.models import NOTE_CONTRACT_REVISION, Note, NoteEvents
from tabgen.core.pipeline import ProgressCallback, null_progress

STAGE = "transcription"
MODEL_NAME = "basic-pitch-icassp2022"
BACKEND = "onnx"
MODEL_VERSION = f"{MODEL_NAME}-{BACKEND}"


@dataclass(frozen=True)
class InstrumentProfile:
    """Frequency bounds (Hz) passed to Basic Pitch for one instrument."""

    minimum_frequency: float
    maximum_frequency: float


INSTRUMENT_PROFILES: dict[str, InstrumentProfile] = {
    # ~B1 (61.7 Hz, covers drop-B low string) up to ~B6: high-fret
    # fundamentals on the high E string plus comfortable headroom.
    "guitar": InstrumentProfile(minimum_frequency=60.0, maximum_frequency=2000.0),
    # ~A0 (27.5 Hz; covers a 5-string low B at 30.9 Hz) up to ~G4 (392 Hz),
    # the practical top of bass fundamentals. Capping the range here keeps
    # low notes such as E1 (41.2 Hz) from being folded up an octave.
    "bass": InstrumentProfile(minimum_frequency=28.0, maximum_frequency=400.0),
}

# Raw basic_pitch note-event tuple:
# (start_s, end_s, pitch_midi, amplitude, per-frame bend list | None).
RawNoteEvent = tuple[float, float, int, float, Optional[list[int]]]

# Runs the model for (audio_path, profile) and returns the raw note events.
Predictor = Callable[[Path, InstrumentProfile], list[RawNoteEvent]]


class TranscriptionError(RuntimeError):
    """Raised when the transcription stage cannot run."""


def transcription_version(instrument: str) -> str:
    """Cache version of the transcription stage for one instrument.

    Pins the model, the instrument profile and the Note contract revision,
    so a schema change of :class:`~tabgen.core.models.Note` (e.g. the
    ``bends`` field) turns old cache entries into misses.
    """
    return f"{MODEL_VERSION}-{instrument}+note-{NOTE_CONTRACT_REVISION}"


@dataclass
class TranscriptionResult:
    """Output of :func:`transcribe`: the note events (bends live on notes).

    The pitch-bend data now lives on each :attr:`Note.bends
    <tabgen.core.models.Note.bends>`. ``bends`` is kept as a compatibility
    mirror parallel to ``note_events.notes``: when given at construction,
    each non-``None`` entry is copied onto the matching note that has no
    bends yet; afterwards it is always rebuilt from the notes.
    """

    note_events: NoteEvents
    bends: list[list[int] | None] = field(default_factory=list)

    def __post_init__(self) -> None:
        notes = self.note_events.notes
        for note, bend in zip(notes, self.bends):
            if bend is not None and note.bends is None:
                note.bends = [int(b) for b in bend]
        self.bends = [
            list(note.bends) if note.bends is not None else None for note in notes
        ]


def _default_predictor(
    audio_path: Path, profile: InstrumentProfile
) -> list[RawNoteEvent]:
    """Run the real Basic Pitch model (imported lazily: it is heavy)."""
    from basic_pitch.inference import predict

    # predict() unconditionally writes a banner to stdout; swallow it to
    # keep core silent (T20 purity applies in spirit to runtime output).
    with contextlib.redirect_stdout(io.StringIO()):
        _, _, note_events = predict(
            str(audio_path),
            minimum_frequency=profile.minimum_frequency,
            maximum_frequency=profile.maximum_frequency,
        )
    return note_events


def _to_result(
    raw_events: list[RawNoteEvent], instrument: str
) -> TranscriptionResult:
    """Convert raw basic_pitch tuples (numpy scalars) to the stage contract."""
    ordered = sorted(raw_events, key=lambda ev: (float(ev[0]), int(ev[2])))
    notes: list[Note] = []
    for start_s, end_s, pitch_midi, amplitude, *rest in ordered:
        amp = float(amplitude)
        raw_bend = rest[0] if rest else None
        notes.append(
            Note(
                pitch_midi=int(pitch_midi),
                start_s=float(start_s),
                end_s=float(end_s),
                velocity=amp,
                confidence=amp,
                bends=[int(b) for b in raw_bend] if raw_bend else None,
            )
        )
    return TranscriptionResult(
        note_events=NoteEvents(
            notes=notes, instrument=instrument, model_version=MODEL_VERSION
        ),
    )


def _payload_from_result(result: TranscriptionResult) -> dict[str, Any]:
    # Bends travel inside each note (Note.bends); no parallel list.
    return {"note_events": result.note_events.to_dict()}


def _result_from_payload(payload: dict[str, Any]) -> TranscriptionResult:
    return TranscriptionResult(
        note_events=NoteEvents.from_dict(payload["note_events"])
    )


def transcribe(
    input_path: str | Path,
    instrument: str = "guitar",
    on_progress: ProgressCallback = null_progress,
    cache: StageCache | None = None,
    predictor: Predictor = _default_predictor,
) -> tuple[TranscriptionResult, bool]:
    """Transcribe an audio file (typically a stem) into note events.

    Returns ``(result, cache_hit)``. The instrument selects the frequency
    profile and is part of the cache key, so the same stem can be cached
    per instrument independently.
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise TranscriptionError(f"input audio not found: {input_path}")
    profile = INSTRUMENT_PROFILES.get(instrument)
    if profile is None:
        known = ", ".join(sorted(INSTRUMENT_PROFILES))
        raise TranscriptionError(
            f"unknown instrument {instrument!r}; expected one of: {known}"
        )
    if cache is None:
        cache = StageCache(input_path)

    version = transcription_version(instrument)
    cached = cache.get(STAGE, version)
    if cached is not None:
        on_progress(STAGE, 100.0)
        return _result_from_payload(cached), True

    on_progress(STAGE, 0.0)
    raw_events = predictor(input_path, profile)
    result = _to_result(raw_events, instrument)
    cache.put(STAGE, version, _payload_from_result(result))
    on_progress(STAGE, 100.0)
    return result, False
