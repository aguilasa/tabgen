"""Stage contract dataclasses: JSON round-trip and plain-serializability."""

import json

import pytest

from tabgen.core.models import (
    AnalysisResult,
    ChordSegment,
    Note,
    NoteEvents,
    SeparationResult,
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
    TabScore(
        tuning_midi=[40, 45, 50, 55, 59, 64],
        capo_fret=2,
        events=[{"string": 6, "fret": 0, "start_s": 0.0, "duration_s": 0.5}],
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
