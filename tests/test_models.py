"""Stage contract dataclasses: JSON round-trip and plain-serializability."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from tabgen.core.cache import StageCache
from tabgen.core.models import (
    BASS_STANDARD_TUNING,
    GUITAR_STANDARD_TUNING,
    SLIDE_DOWN,
    SLIDE_UP,
    TECHNIQUE_BEND,
    TECHNIQUE_HAMMER_ON,
    TECHNIQUE_KINDS,
    TECHNIQUE_PULL_OFF,
    TECHNIQUE_SLIDE,
    AnalysisResult,
    ChordSegment,
    MeasureChord,
    Note,
    NoteEvents,
    SeparationResult,
    TabNote,
    TabScore,
    Technique,
)

FIXTURES = Path(__file__).parent / "fixtures"

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


def _tab_note(fret: int, beat: int, technique: Technique | None = None) -> TabNote:
    return TabNote(
        string=3,
        fret=fret,
        measure=1,
        beat=beat,
        subdivision=0,
        duration_subdivisions=4,
        start_s=0.5 * (beat - 1),
        end_s=0.5 * beat,
        technique=technique,
    )


def test_tab_score_round_trip_with_every_technique():
    score = TabScore(
        tempo_bpm=120.0,
        events=[
            _tab_note(
                7,
                1,
                Technique(
                    kind=TECHNIQUE_BEND,
                    bend_semitones=2.0,
                    bend_curve=[0.0, 1.0, 2.0, 2.0],
                ),
            ),
            _tab_note(
                5,
                2,
                Technique(
                    kind=TECHNIQUE_SLIDE, slide_direction=SLIDE_UP, target_fret=7
                ),
            ),
            _tab_note(7, 3, Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=9)),
            _tab_note(9, 4, Technique(kind=TECHNIQUE_PULL_OFF, target_fret=7)),
            _tab_note(7, 4),
        ],
    )
    restored = TabScore.from_json(score.to_json())
    assert restored == score
    kinds = [e.technique.kind if e.technique else None for e in restored.events]
    assert kinds == [*TECHNIQUE_KINDS, None]
    assert all(
        isinstance(e.technique, Technique) for e in restored.events[:4]
    )
    assert restored.events[1].technique.slide_direction == SLIDE_UP
    assert restored.events[0].technique.bend_curve == [0.0, 1.0, 2.0, 2.0]


def test_note_events_round_trip_with_bends():
    events = NoteEvents(
        notes=[
            Note(pitch_midi=64, start_s=0.0, end_s=0.5, bends=[0, 1, 3, 6, 6]),
            Note(pitch_midi=67, start_s=0.5, end_s=1.0),
            Note(pitch_midi=62, start_s=1.0, end_s=1.5, bends=[0, -1, -3]),
        ]
    )
    restored = NoteEvents.from_json(events.to_json())
    assert restored == events
    assert [n.bends for n in restored.notes] == [[0, 1, 3, 6, 6], None, [0, -1, -3]]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": "vibrato"},
        {"kind": TECHNIQUE_BEND},  # bend without a target
        {"kind": TECHNIQUE_SLIDE},  # slide without a direction
        {"kind": TECHNIQUE_SLIDE, "slide_direction": "sideways"},
    ],
)
def test_technique_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        Technique(**kwargs)


def test_slide_down_is_valid():
    t = Technique(kind=TECHNIQUE_SLIDE, slide_direction=SLIDE_DOWN)
    assert t.target_fret is None


def test_pre_technique_fixture_loads_with_empty_techniques():
    # contracts_v1.json was produced by the TAB_FORMAT_VERSION 1 /
    # Note revision 1 to_json (before bends and techniques existed).
    fixture = json.loads((FIXTURES / "contracts_v1.json").read_text())
    assert fixture["tab_format_version"] == 1
    raw_events = fixture["tab_score"]["events"]
    assert raw_events and all("technique" not in e for e in raw_events)
    raw_notes = fixture["note_events"]["notes"]
    assert raw_notes and all("bends" not in n for n in raw_notes)

    score = TabScore.from_json(json.dumps(fixture["tab_score"]))
    assert len(score.events) == len(raw_events)
    assert all(e.technique is None for e in score.events)
    events = NoteEvents.from_json(json.dumps(fixture["note_events"]))
    assert len(events.notes) == len(raw_notes)
    assert all(n.bends is None for n in events.notes)


# Cache versions as computed before the technique contract (pinned formula of
# the previous revision): an entry stored under them must now be a miss.
OLD_TRANSCRIPTION_VERSION = "basic-pitch-icassp2022-onnx-guitar"


def _old_tablature_version(configs) -> str:
    from tabgen.core.pipeline import TABLATURE_PIPELINE_REVISION, analysis_version
    from tabgen.core.transcription.basic_pitch import MODEL_VERSION

    params = {name: asdict(cfg) for name, cfg in sorted(configs.items())}
    digest = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    return (
        f"tab-1+rev-{TABLATURE_PIPELINE_REVISION}"
        f"+{analysis_version()}+{MODEL_VERSION}+params-{digest}"
    )


def test_transcription_cache_version_changed_old_entry_misses(tmp_path):
    from tabgen.core.transcription import basic_pitch as bp

    audio = tmp_path / "stem.wav"
    audio.write_bytes(b"not really audio")
    cache = StageCache(audio)
    cache.put(bp.STAGE, OLD_TRANSCRIPTION_VERSION, {"note_events": {"notes": []}})

    new_version = bp.transcription_version("guitar")
    assert new_version != OLD_TRANSCRIPTION_VERSION
    assert cache.get(bp.STAGE, new_version) is None

    calls = []

    def predictor(path, profile):
        calls.append(path)
        return [(0.0, 0.5, 64, 0.8, [0, 1, 2])]

    result, hit = bp.transcribe(audio, "guitar", cache=cache, predictor=predictor)
    assert not hit and len(calls) == 1  # the old entry was not reused
    assert result.note_events.notes[0].bends == [0, 1, 2]
    assert result.bends == [[0, 1, 2]]  # compat mirror


def test_tablature_cache_version_changed_old_entry_misses(tmp_path):
    from tabgen.core.pipeline import (
        TABLATURE_STAGE,
        _fretting_configs,
        tablature_version,
    )

    configs = _fretting_configs(("guitar",), {"guitar": GUITAR_STANDARD_TUNING}, {})
    old_version = _old_tablature_version(configs)
    new_version = tablature_version(configs)
    assert new_version != old_version

    audio = tmp_path / "song.wav"
    audio.write_bytes(b"not really audio")
    cache = StageCache(audio)
    cache.put(TABLATURE_STAGE, old_version, {"scores": []})
    assert cache.get(TABLATURE_STAGE, old_version) is not None
    assert cache.get(TABLATURE_STAGE, new_version) is None
