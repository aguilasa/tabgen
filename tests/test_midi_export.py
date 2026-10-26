"""Tests for the MIDI export stage (NoteEvents -> .mid file)."""

from pathlib import Path

import mido
import pretty_midi
import pytest

from tabgen.core.export import midi as midi_export
from tabgen.core.models import Note, NoteEvents


def _messages(path: Path, kind: str) -> list:
    """All messages of one type across every track of a MIDI file."""
    mid = mido.MidiFile(path)
    return [msg for track in mid.tracks for msg in track if msg.type == kind]


def test_export_writes_mid_file_readable_by_mido(tmp_path: Path) -> None:
    events = NoteEvents(
        notes=[
            Note(pitch_midi=60, start_s=0.5, end_s=1.0, velocity=0.8),
            Note(pitch_midi=64, start_s=1.25, end_s=2.0, velocity=0.5),
        ],
        instrument="guitar",
    )

    path = midi_export.export_midi(events, tmp_path / "song.guitar.mid")

    assert path.is_file()
    note_ons = [m for m in _messages(path, "note_on") if m.velocity > 0]
    assert len(note_ons) >= 1
    assert sorted(m.note for m in note_ons) == [60, 64]
    # No bends were provided, so no pitch-wheel messages are written.
    assert _messages(path, "pitchwheel") == []


def test_timestamps_survive_the_round_trip_unquantized(tmp_path: Path) -> None:
    events = NoteEvents(
        notes=[Note(pitch_midi=69, start_s=0.371, end_s=1.234, velocity=1.0)],
        instrument="guitar",
    )

    path = midi_export.export_midi(events, tmp_path / "a4.mid")

    reloaded = pretty_midi.PrettyMIDI(str(path))
    (note,) = reloaded.instruments[0].notes
    # Only MIDI tick resolution applies (~2 ms at the default tempo map).
    assert abs(note.start - 0.371) < 0.01
    assert abs(note.end - 1.234) < 0.01
    assert note.pitch == 69


def test_bends_become_pitchwheel_messages(tmp_path: Path) -> None:
    events = NoteEvents(
        notes=[
            Note(pitch_midi=45, start_s=0.0, end_s=1.0),
            Note(pitch_midi=47, start_s=1.5, end_s=2.0),
        ],
        instrument="bass",
    )

    path = midi_export.export_midi(
        events, tmp_path / "bends.mid", bends=[[0, 1, 2, 3], None]
    )

    wheels = _messages(path, "pitchwheel")
    assert wheels  # bends were written
    # Bin 3 = 1 semitone = half of the ±2 semitone wheel range -> 4096.
    assert max(m.pitch for m in wheels) == 4096
    # A reset to 0 follows the bent note so later notes are unaffected.
    assert wheels[-1].pitch == 0


def test_mismatched_bends_length_raises(tmp_path: Path) -> None:
    events = NoteEvents(
        notes=[Note(pitch_midi=60, start_s=0.0, end_s=1.0)], instrument="guitar"
    )
    with pytest.raises(midi_export.MidiExportError, match="bends length"):
        midi_export.export_midi(events, tmp_path / "bad.mid", bends=[None, None])


def test_empty_note_events_still_write_a_valid_file(tmp_path: Path) -> None:
    path = midi_export.export_midi(
        NoteEvents(instrument="bass"), tmp_path / "empty.mid"
    )
    mido.MidiFile(path)  # reopens without error
    assert _messages(path, "note_on") == []


def test_velocity_is_clamped_to_midi_range(tmp_path: Path) -> None:
    events = NoteEvents(
        notes=[
            Note(pitch_midi=60, start_s=0.0, end_s=0.5, velocity=0.0),
            Note(pitch_midi=62, start_s=0.6, end_s=1.0, velocity=2.0),
        ],
        instrument="guitar",
    )

    path = midi_export.export_midi(events, tmp_path / "vel.mid")

    velocities = sorted(
        m.velocity for m in _messages(path, "note_on") if m.velocity > 0
    )
    assert velocities == [1, 127]
