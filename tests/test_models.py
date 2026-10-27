"""Stage contract dataclasses: JSON round-trip and plain-serializability."""

import json

import pytest

from tabgen.core.models import (
    BASS_STANDARD_TUNING,
    GUITAR_STANDARD_TUNING,
    AnalysisResult,
    ChordSegment,
    MeasureChord,
    Note,
    NoteEvents,
    SeparationResult,
    TabNote,
    TabScore,
)

SAMPLES = [
    SeparationResult(
        stems={"guitar": "/tmp/guitar.wav", "other": "/tmp/other.wav"},
        sample_rate=44100,
        model_version="demucs-4.0",
    ),
    AnalysisResult(
        tempo_bpm=120.5,
        beat_times=[0.5, 1.0, 1.5],
        downbeat_times=[0.5],
        key="E minor",
        key_confidence=0.92,
        chords=[
            ChordSegment(start_s=0.0, end_s=2.0, label="E:min"),
            ChordSegment(start_s=2.0, end_s=4.0, label="A:min"),
        ],
        tuning_offset_cents=-12.3,
    ),
    ChordSegment(start_s=1.5, end_s=3.0, label="C:maj"),
    Note(pitch_midi=64, start_s=0.25, end_s=0.75, velocity=0.9, confidence=0.87),
    NoteEvents(
        notes=[
            Note(pitch_midi=40, start_s=0.0, end_s=0.5),
            Note(pitch_midi=52, start_s=0.5, end_s=1.0, velocity=0.5),
        ],
        instrument="guitar",
        model_version="basic-pitch-1.0",
    ),
    TabNote(
        string=1,
        fret=3,
        measure=2,
        beat=1,
        subdivision=2,
        duration_subdivisions=4,
        start_s=2.01,
        end_s=2.49,
    ),
    MeasureChord(measure=1, label="E:min"),
    TabScore(
        instrument="guitar",
        tuning_midi=GUITAR_STANDARD_TUNING,
        capo_fret=2,
        tempo_bpm=120.0,
        key="E minor",
        time_signature=[4, 4],
        events=[
            TabNote(
                string=1,
                fret=0,
                measure=1,
                beat=1,
                subdivision=0,
                duration_subdivisions=2,
                start_s=0.0,
                end_s=0.5,
            ),
        ],
        chords=[MeasureChord(measure=1, label="E:min")],
    ),
]


@pytest.mark.parametrize("obj", SAMPLES, ids=lambda o: type(o).__name__)
def test_json_round_trip_preserves_equality(obj):
    restored = type(obj).from_json(obj.to_json())
    assert restored == obj


@pytest.mark.parametrize("obj", SAMPLES, ids=lambda o: type(o).__name__)
def test_to_dict_is_json_dumpable_without_custom_encoder(obj):
    # Must not raise: fields are builtins only (no torch/numpy objects).
    payload = json.dumps(obj.to_dict())
    assert json.loads(payload) == obj.to_dict()


def test_analysis_result_round_trip_rebuilds_chord_segments():
    result = AnalysisResult(
        tempo_bpm=98.0,
        key="A minor",
        key_confidence=0.81,
        chords=[
            ChordSegment(start_s=0.0, end_s=1.75, label="A:min"),
            ChordSegment(start_s=1.75, end_s=3.5, label="F:maj"),
            ChordSegment(start_s=3.5, end_s=5.25, label="G:maj"),
        ],
    )
    restored = AnalysisResult.from_json(result.to_json())
    assert all(isinstance(chord, ChordSegment) for chord in restored.chords)
    assert restored == result


def test_analysis_result_from_dict_defaults_chords_when_absent():
    # Backward compatibility: old payloads predate the ``chords`` field.
    old_payload = {
        "tempo_bpm": 120.0,
        "beat_times": [0.5],
        "downbeat_times": [0.5],
        "key": "E minor",
        "tuning_offset_cents": -3.0,
    }
    restored = AnalysisResult.from_dict(old_payload)
    assert restored.chords == []
    assert restored.key_confidence == 0.0


def test_note_events_round_trip_rebuilds_note_instances():
    events = NoteEvents(notes=[Note(pitch_midi=60, start_s=0.0, end_s=1.0)])
    restored = NoteEvents.from_json(events.to_json())
    assert all(isinstance(note, Note) for note in restored.notes)
    assert restored == events


def test_tab_score_round_trip_for_bass_with_notes_and_chord():
    t = TabScore(
        instrument="bass",
        tuning_midi=list(BASS_STANDARD_TUNING),
        capo_fret=0,
        tempo_bpm=96.0,
        key="A minor",
        time_signature=[3, 4],
        events=[
            TabNote(
                string=1,
                fret=5,
                measure=1,
                beat=1,
                subdivision=0,
                duration_subdivisions=4,
                start_s=0.0,
                end_s=0.62,
            ),
            TabNote(
                string=2,
                fret=0,
                measure=1,
                beat=2,
                subdivision=0,
                duration_subdivisions=2,
                start_s=0.63,
                end_s=0.94,
            ),
            TabNote(
                string=3,
                fret=2,
                measure=2,
                beat=1,
                subdivision=1,
                duration_subdivisions=3,
                start_s=1.27,
                end_s=1.74,
            ),
        ],
        chords=[
            MeasureChord(measure=1, label="A:min"),
            MeasureChord(measure=2, label="E:maj"),
        ],
    )
    assert len(t.tuning_midi) == 4
    restored = TabScore.from_json(t.to_json())
    assert all(isinstance(event, TabNote) for event in restored.events)
    assert all(isinstance(chord, MeasureChord) for chord in restored.chords)
    assert restored == t


def test_tab_score_from_dict_defaults_events_and_chords_when_absent():
    # Backward compatibility: old payloads predate typed events and chords.
    old_payload = {"tuning_midi": [40, 45, 50, 55, 59, 64], "capo_fret": 2}
    restored = TabScore.from_dict(old_payload)
    assert restored.events == []
    assert restored.chords == []
    assert restored.instrument == "guitar"
    assert restored.time_signature == [4, 4]
