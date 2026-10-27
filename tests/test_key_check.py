"""Tests for the key cross-check (madmom key vs note histogram).

All notes are synthetic: plain :class:`Note` lists wrapped in
:class:`NoteEvents`, no audio or models involved.
"""

from tabgen.core.analysis.key_check import (
    MIN_MADMOM_CONFIDENCE,
    check_key,
    pitch_class_histogram,
    relative_key,
    score_keys,
)
from tabgen.core.models import Note, NoteEvents

# MIDI pitch classes used below (octave 4-ish).
C4, D4, E4, F4, G3, A3, B3, FS4 = 60, 62, 64, 65, 55, 57, 59, 66

G_MAJOR_SCALE = (G3, A3, B3, C4, D4, E4, FS4)
C_MAJOR_SCALE = (C4, D4, E4, F4, G3, A3, B3)


def _events(
    pitches: tuple[int, ...],
    duration_s: float = 0.5,
    emphasized: int | None = None,
    instrument: str = "guitar",
) -> NoteEvents:
    """NoteEvents with one note per pitch; ``emphasized`` lasts 4x longer."""
    notes = []
    start = 0.0
    for pitch in pitches:
        duration = duration_s * (4.0 if pitch == emphasized else 1.0)
        notes.append(Note(pitch_midi=pitch, start_s=start, end_s=start + duration))
        start += duration
    return NoteEvents(notes=notes, instrument=instrument)


def test_g_major_scale_with_emphasized_tonic_scores_g_major_first() -> None:
    events = _events(G_MAJOR_SCALE, emphasized=G3)

    scores = score_keys(pitch_class_histogram([events]))

    assert max(scores, key=lambda name: scores[name]) == "G major"

    result = check_key("G major", 0.9, [events])
    assert result.histogram_key == "G major"
    assert result.agreement and not result.switched
    assert result.key == "G major"
    assert result.reason == "match"


def test_relative_keys_are_concordant() -> None:
    # madmom says A minor, the notes spell C major: relatives agree.
    events = _events(C_MAJOR_SCALE, emphasized=C4)

    result = check_key("A minor", 0.8, [events])

    assert result.histogram_key == "C major"
    assert result.agreement
    assert not result.switched
    assert result.key == "A minor"
    assert result.reason == "relative"


def test_low_confidence_madmom_overridden_by_strong_histogram() -> None:
    # madmom guesses E major with low confidence while guitar and bass
    # both play C major: the histogram's key wins and the switch is
    # flagged.
    guitar = _events(C_MAJOR_SCALE, emphasized=C4, instrument="guitar")
    bass = _events((C4 - 24, G3 - 12), duration_s=1.0, instrument="bass")

    result = check_key("E major", 0.3, [guitar, bass])

    assert result.histogram_key == "C major"
    assert result.switched
    assert result.key == "C major"
    assert result.reason == "histogram_override"
    assert not result.agreement
    assert result.margin > 0.0
    assert 0.0 < result.key_confidence <= 1.0


def test_confident_madmom_key_is_kept_despite_disagreement() -> None:
    events = _events(C_MAJOR_SCALE, emphasized=C4)

    result = check_key("E major", MIN_MADMOM_CONFIDENCE, [events])

    assert result.key == "E major"
    assert not result.switched
    assert result.reason == "madmom_confident"
    assert result.key_confidence == MIN_MADMOM_CONFIDENCE


def test_no_notes_keeps_madmom_key() -> None:
    result = check_key("D major", 0.4, [NoteEvents(notes=[])])

    assert result.key == "D major"
    assert not result.switched
    assert result.reason == "no_notes"
    assert result.histogram_key == ""


def test_missing_madmom_key_adopts_histogram_key() -> None:
    events = _events(G_MAJOR_SCALE, emphasized=G3)

    result = check_key("", 0.0, [events])

    assert result.key == "G major"
    assert result.switched
    assert result.reason == "no_madmom_key"


def test_relative_key_mapping() -> None:
    assert relative_key("C major") == "A minor"
    assert relative_key("A minor") == "C major"
    assert relative_key("F# major") == "Eb minor"
    assert relative_key("Gb major") == "Eb minor"
