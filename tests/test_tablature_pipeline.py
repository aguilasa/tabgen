"""Tests for the tablature pipeline orchestration (run_tablature).

Separation, analysis and transcription are injected fakes (no Demucs,
madmom or Basic Pitch); the fretting DP runs for real on the first pass.
The cache tests prove that a second run is served entirely from the
``tablature`` cache entry: every injected stage raises if called.
"""

from pathlib import Path

import guitarpro
import numpy as np
import pytest
import soundfile
from music21 import converter

from tabgen.core import pipeline
from tabgen.core.models import (
    AnalysisResult,
    ChordSegment,
    Note,
    NoteEvents,
    SeparationResult,
)
from tabgen.core.pipeline import (
    AnalysisSummary,
    PipelineError,
    resolve_export_format,
    resolve_tuning,
    run_tablature,
)
from tabgen.core.transcription.basic_pitch import TranscriptionResult

# 120 BPM: one beat every 0.5 s, 4/4, first downbeat at 0.5 s.
BEATS = [0.5 + 0.5 * i for i in range(17)]
DOWNBEATS = BEATS[::4]
CHORDS = [
    ChordSegment(start_s=0.5, end_s=2.5, label="A:min"),
    ChordSegment(start_s=2.5, end_s=4.5, label="C:maj"),
    ChordSegment(start_s=4.5, end_s=8.5, label="N"),
]

# A-minor pentatonic run (guitar) and a root line (bass), one note per beat.
GUITAR_PITCHES = [57, 60, 62, 64, 67, 69, 72, 74]
BASS_PITCHES = [33, 33, 36, 36, 31, 31, 33, 33]


def write_input(tmp_path: Path, name: str = "song.wav") -> Path:
    path = tmp_path / name
    soundfile.write(str(path), np.zeros((4410, 2), dtype=np.float32), 44100)
    return path


def _notes(pitches: list[int]) -> NoteEvents:
    return NoteEvents(
        notes=[
            Note(pitch_midi=p, start_s=0.5 + 0.5 * i, end_s=0.95 + 0.5 * i)
            for i, p in enumerate(pitches)
        ]
    )


def make_fakes(tmp_path: Path, calls: list[str]):
    stems_dir = tmp_path / "stems"
    stems_dir.mkdir(exist_ok=True)
    stems = {}
    for name in ("guitar", "bass", "drums", "vocals", "other"):
        stem = stems_dir / f"{name}.wav"
        stem.touch()
        stems[name] = str(stem)

    def fake_separate(input_path, device=None, on_progress=pipeline.null_progress):
        calls.append("separate")
        on_progress("separation", 100.0)
        return SeparationResult(stems=stems, model_version="fake"), True

    def fake_analysis(input_path, device=None, on_progress=pipeline.null_progress,
                      cache=None):
        calls.append("analysis")
        for stage in pipeline.ANALYSIS_STAGES:
            on_progress(stage, 100.0)
        return AnalysisSummary(
            input_path=str(input_path),
            separation_cache_hit=True,
            analysis_cache_hit=False,
            result=AnalysisResult(
                tempo_bpm=120.0,
                beat_times=list(BEATS),
                downbeat_times=list(DOWNBEATS),
                key="A minor",
                key_confidence=0.9,
                chords=list(CHORDS),
            ),
        )

    def fake_transcribe(input_path, instrument="guitar",
                        on_progress=pipeline.null_progress):
        calls.append(f"transcribe:{instrument}")
        on_progress("transcription", 100.0)
        pitches = GUITAR_PITCHES if instrument == "guitar" else BASS_PITCHES
        events = _notes(pitches)
        events.instrument = instrument
        return TranscriptionResult(note_events=events), False

    return fake_separate, fake_analysis, fake_transcribe


def failing(name: str):
    def fail(*args, **kwargs):
        raise AssertionError(f"{name} must not run on a tablature cache hit")

    return fail


def run_with_fakes(tmp_path: Path, output: Path, calls: list[str], **kwargs):
    separate, analysis, transcribe = make_fakes(tmp_path, calls)
    return run_tablature(
        tmp_path / "song.wav",
        output_path=output,
        separate_fn=separate,
        analysis_fn=analysis,
        transcribe_fn=transcribe,
        **kwargs,
    )


def test_gp5_export_has_guitar_and_bass_tracks_with_notes(tmp_path):
    write_input(tmp_path)
    calls: list[str] = []
    out = tmp_path / "out.gp5"
    summary = run_with_fakes(tmp_path, out, calls)

    assert summary.cache_hit is False
    assert summary.format == "gp5"
    assert [s.instrument for s in summary.scores] == ["guitar", "bass"]
    assert summary.key_check["key"] == "A minor"
    assert summary.unassigned == {"guitar": 0, "bass": 0}
    for score, grid in zip(summary.scores, summary.beat_grids):
        assert len(score.events) == 8
        assert grid == [4] * 8
        assert score.time_signature == [4, 4]
        assert score.tempo_bpm == 120.0
    # Chord changes land on measures 1 and 2; "N" is never annotated.
    assert [(c.measure, c.label) for c in summary.scores[0].chords] == [
        (1, "A:min"),
        (2, "C:maj"),
    ]

    song = guitarpro.parse(str(out))
    assert len(song.tracks) == 2
    for track, n_strings in zip(song.tracks, (6, 4)):
        assert len(track.strings) == n_strings
        notes = [
            note
            for measure in track.measures
            for voice in measure.voices
            for beat in voice.beats
            for note in beat.notes
        ]
        assert len(notes) >= 1


def test_musicxml_and_ascii_outputs(tmp_path):
    write_input(tmp_path)
    calls: list[str] = []
    xml_out = tmp_path / "out.musicxml"
    run_with_fakes(tmp_path, xml_out, calls)
    parsed = converter.parse(str(xml_out))
    assert len(parsed.parts) == 2
    assert len(list(parsed.recurse().notes)) >= 16

    txt_out = tmp_path / "out.txt"
    summary = run_with_fakes(tmp_path, txt_out, calls)
    assert summary.cache_hit is True
    text = txt_out.read_text(encoding="utf-8")
    assert text.strip()
    assert "Guitar" in text or "guitar" in text

    forced = tmp_path / "forced.out"
    summary = run_with_fakes(tmp_path, forced, calls, fmt="ascii")
    assert summary.format == "ascii"
    assert forced.read_text(encoding="utf-8") == text


def test_second_run_is_served_from_cache_without_any_stage(tmp_path):
    write_input(tmp_path)
    calls: list[str] = []
    run_with_fakes(tmp_path, tmp_path / "first.gp5", calls)
    assert "analysis" in calls and "transcribe:guitar" in calls

    events: list[tuple[str, float]] = []
    summary = run_tablature(
        tmp_path / "song.wav",
        output_path=tmp_path / "second.gp5",
        on_progress=lambda stage, pct: events.append((stage, pct)),
        separate_fn=failing("Demucs"),
        analysis_fn=failing("madmom"),
        transcribe_fn=failing("Basic Pitch"),
        fretting_fn=failing("fretting DP"),
    )
    assert summary.cache_hit is True
    assert len(summary.scores) == 2
    assert (tmp_path / "second.gp5").is_file()
    finished = {stage for stage, pct in events if pct == 100.0}
    assert {"quantization", "fretting:guitar", "fretting:bass", "export"} <= finished


def test_changing_tuning_or_capo_invalidates_the_cache(tmp_path):
    write_input(tmp_path)
    calls: list[str] = []
    run_with_fakes(tmp_path, tmp_path / "a.gp5", calls)
    calls.clear()
    summary = run_with_fakes(
        tmp_path,
        tmp_path / "b.gp5",
        calls,
        tunings={"guitar": resolve_tuning("drop-d", "guitar")},
    )
    assert summary.cache_hit is False
    assert summary.scores[0].tuning_midi == [38, 45, 50, 55, 59, 64]
    calls.clear()
    summary = run_with_fakes(tmp_path, tmp_path / "c.gp5", calls, capos={"guitar": 2})
    assert summary.cache_hit is False
    assert summary.scores[0].capo_fret == 2


def test_progress_reaches_100_for_quantization_fretting_and_export(tmp_path):
    write_input(tmp_path)
    calls: list[str] = []
    events: list[tuple[str, float]] = []
    run_with_fakes(
        tmp_path,
        tmp_path / "out.gp5",
        calls,
        on_progress=lambda stage, pct: events.append((stage, pct)),
    )
    final = {}
    for stage, pct in events:
        final[stage] = pct
    for stage in ("quantization", "fretting:guitar", "fretting:bass", "export"):
        assert final[stage] == 100.0, stage
    stages = [stage for stage, _ in events]
    assert stages.index("quantization") < stages.index("fretting:guitar")
    assert stages.index("fretting:bass") < stages.index("export")


def test_single_instrument_and_input_errors(tmp_path):
    write_input(tmp_path)
    calls: list[str] = []
    summary = run_with_fakes(
        tmp_path, tmp_path / "g.gp5", calls, instruments=["guitar"]
    )
    assert [s.instrument for s in summary.scores] == ["guitar"]
    assert "transcribe:bass" not in calls

    with pytest.raises(PipelineError, match="unsupported instrument"):
        run_with_fakes(tmp_path, tmp_path / "x.gp5", calls, instruments=["drums"])
    with pytest.raises(PipelineError, match="cannot infer the export format"):
        run_with_fakes(tmp_path, tmp_path / "x.pdf", calls)
    with pytest.raises(PipelineError, match="not found"):
        run_tablature(tmp_path / "missing.wav")


def test_resolve_tuning_and_format():
    assert resolve_tuning(None, "guitar") == [40, 45, 50, 55, 59, 64]
    assert resolve_tuning(None, "bass") == [28, 33, 38, 43]
    assert resolve_tuning("Drop-D", "guitar") == [38, 45, 50, 55, 59, 64]
    assert resolve_tuning("D2,A2,D3,G3,B3,E4", "guitar") == [38, 45, 50, 55, 59, 64]
    assert resolve_tuning("Eb1,Ab1,Db2,Gb2", "bass") == [27, 32, 37, 42]
    assert resolve_tuning("38,45,50,55,59,64", "guitar")[0] == 38
    with pytest.raises(PipelineError, match="low-to-high"):
        resolve_tuning("E4,B3,G3,D3,A2,E2", "guitar")
    with pytest.raises(PipelineError, match="invalid note name"):
        resolve_tuning("H2,A2", "guitar")

    assert resolve_export_format("x.gp5") == "gp5"
    assert resolve_export_format("x.musicxml") == "musicxml"
    assert resolve_export_format("x.XML") == "musicxml"
    assert resolve_export_format("x.txt") == "ascii"
    assert resolve_export_format("x.gp5", "ascii") == "ascii"
    with pytest.raises(PipelineError, match="unknown export format"):
        resolve_export_format("x.gp5", "pdf")


def test_notes_quantized_to_one_onset_are_fretted_as_one_chord(tmp_path):
    """Onsets 50-60 ms apart (beyond the DP's 30 ms chord window) that snap
    to the same sixteenth must still land on distinct strings, with a
    repeated pitch kept once; otherwise the .gp5 beat is unreadable."""
    write_input(tmp_path)
    calls: list[str] = []
    separate, analysis, _ = make_fakes(tmp_path, calls)
    close_onsets = NoteEvents(
        notes=[
            Note(pitch_midi=55, start_s=1.00, end_s=1.40),
            Note(pitch_midi=59, start_s=1.05, end_s=1.40),
            Note(pitch_midi=55, start_s=1.06, end_s=1.20),
            Note(pitch_midi=62, start_s=1.50, end_s=1.90),
        ]
    )

    def transcribe(input_path, instrument="guitar",
                   on_progress=pipeline.null_progress):
        return TranscriptionResult(note_events=close_onsets), False

    out = tmp_path / "chord.gp5"
    summary = run_tablature(
        tmp_path / "song.wav",
        output_path=out,
        instruments=["guitar"],
        separate_fn=separate,
        analysis_fn=analysis,
        transcribe_fn=transcribe,
    )
    events = summary.scores[0].events
    first = [e for e in events if (e.measure, e.beat, e.subdivision) == (1, 2, 0)]
    assert len(first) == 2
    assert len({e.string for e in first}) == 2
    song = guitarpro.parse(str(out))
    beat_sizes = [
        len(beat.notes)
        for measure in song.tracks[0].measures
        for beat in measure.voices[0].beats
        if beat.notes
    ]
    assert beat_sizes == [2, 1]
