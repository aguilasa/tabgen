"""Export NoteEvents to a Standard MIDI File (one instrument per file).

Timestamps are written as absolute seconds — pretty_midi converts them
to ticks under its default constant tempo map, so no quantization is
applied beyond MIDI tick resolution.

Pitch bends come from Basic Pitch, which reports them per note as a
list of per-frame offsets in 1/3-semitone bins. Each bin list is spread
evenly across the note's duration and converted to MIDI pitch-wheel
values assuming the standard ±2 semitone bend range; a reset (0) is
written at the note's end so later notes are unaffected.

This module is pure core: no print/typer/rich.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import pretty_midi

from tabgen.core.models import NoteEvents

# General MIDI program numbers (0-based): 25 = Acoustic Guitar (steel),
# 33 = Electric Bass (finger). Unknown instruments fall back to 0 (piano).
GM_PROGRAMS: dict[str, int] = {"guitar": 25, "bass": 33}
DEFAULT_PROGRAM = 0

# Basic Pitch bend bins are thirds of a semitone.
BEND_BIN_SEMITONES = 1.0 / 3.0
# Assumed synth pitch-bend range: ±2 semitones (the GM default).
BEND_RANGE_SEMITONES = 2.0
_PITCH_BEND_MAX = 8191
_PITCH_BEND_MIN = -8192

# Per-note bend data, parallel to NoteEvents.notes (see
# tabgen.core.transcription.basic_pitch.TranscriptionResult.bends).
Bends = Sequence[Optional[Sequence[int]]]


class MidiExportError(RuntimeError):
    """Raised when NoteEvents cannot be written as a MIDI file."""


def _velocity_to_midi(velocity: float) -> int:
    """Map a 0..1 velocity to MIDI 1..127 (floor of 1 keeps notes audible)."""
    return max(1, min(127, round(velocity * 127)))


def _bend_bin_to_wheel(bend_bin: int) -> int:
    """Convert a 1/3-semitone bend bin to a MIDI pitch-wheel value."""
    semitones = bend_bin * BEND_BIN_SEMITONES
    value = round(semitones / BEND_RANGE_SEMITONES * (_PITCH_BEND_MAX + 1))
    return max(_PITCH_BEND_MIN, min(_PITCH_BEND_MAX, value))


def _append_bends(
    instrument: pretty_midi.Instrument,
    note: pretty_midi.Note,
    bend_bins: Sequence[int],
) -> None:
    """Spread per-frame bend bins evenly across the note and add a reset."""
    count = len(bend_bins)
    if count == 0:
        return
    duration = max(note.end - note.start, 0.0)
    for index, bend_bin in enumerate(bend_bins):
        time = note.start + duration * index / count
        instrument.pitch_bends.append(
            pretty_midi.PitchBend(pitch=_bend_bin_to_wheel(int(bend_bin)), time=time)
        )
    instrument.pitch_bends.append(pretty_midi.PitchBend(pitch=0, time=note.end))


def export_midi(
    note_events: NoteEvents,
    output_path: str | Path,
    bends: Bends | None = None,
) -> Path:
    """Write ``note_events`` as a single-instrument MIDI file.

    ``bends`` (optional) must run parallel to ``note_events.notes``; each
    entry is a list of Basic Pitch 1/3-semitone bend bins or ``None``.
    Returns the path of the written file.
    """
    notes = note_events.notes
    if bends is not None and len(bends) != len(notes):
        raise MidiExportError(
            f"bends length {len(bends)} does not match note count {len(notes)}"
        )

    midi = pretty_midi.PrettyMIDI()
    program = GM_PROGRAMS.get(note_events.instrument, DEFAULT_PROGRAM)
    instrument = pretty_midi.Instrument(
        program=program, name=note_events.instrument
    )

    for index, note in enumerate(notes):
        pm_note = pretty_midi.Note(
            velocity=_velocity_to_midi(note.velocity),
            pitch=note.pitch_midi,
            start=note.start_s,
            end=note.end_s,
        )
        instrument.notes.append(pm_note)
        note_bends = bends[index] if bends is not None else None
        if note_bends:
            _append_bends(instrument, pm_note, note_bends)

    midi.instruments.append(instrument)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(output_path))
    return output_path
