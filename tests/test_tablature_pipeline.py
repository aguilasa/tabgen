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


# A bent note (beat 1), then a picked note hammered onto a quieter one
# (beats 2-3, contiguous on one string), then a plain note. Basic Pitch
# bend bins are 1/3 semitone: 6 bins = a whole step held for ~0.38 s.
TECHNIQUE_NOTES = [
    Note(pitch_midi=62, start_s=0.5, end_s=0.95, velocity=0.9,
         bends=[0] * 6 + [6] * 33),
    Note(pitch_midi=69, start_s=1.0, end_s=1.25, velocity=0.9),
    Note(pitch_midi=71, start_s=1.25, end_s=1.45, velocity=0.3),
    Note(pitch_midi=64, start_s=2.0, end_s=2.45, velocity=0.9),
]


def _technique_transcribe(input_path, instrument="guitar",
                          on_progress=pipeline.null_progress):
    events = NoteEvents(notes=[Note(**vars(n)) for n in TECHNIQUE_NOTES])
    return TranscriptionResult(note_events=events), False


# Fixed fingering of TECHNIQUE_NOTES (the hammer pair shares string 1), so
# the detectors see a known layout whatever the DP weights prefer.
TECHNIQUE_FRETS = {62: (3, 7), 69: (1, 5), 71: (1, 7), 64: (1, 0)}


def _technique_fretting(notes, config=None, chords=None):
    from tabgen.core.fretting import FrettedNote, FrettingResult

    return FrettingResult(
        assignments=[FrettedNote(n, *TECHNIQUE_FRETS[n.pitch_midi]) for n in notes]
    )


def _run_techniques(tmp_path: Path, output: Path, **kwargs):
    separate, analysis, _ = make_fakes(tmp_path, [])
    return run_tablature(
        tmp_path / "song.wav",
        output_path=output,
        instruments=["guitar"],
        separate_fn=separate,
        analysis_fn=analysis,
        transcribe_fn=_technique_transcribe,
        fretting_fn=_technique_fretting,
        **kwargs,
    )


def test_pipeline_detects_bend_and_hammer_from_source_notes(tmp_path):
    write_input(tmp_path)
    summary = _run_techniques(tmp_path, tmp_path / "fx.gp5")
    kinds = [
        (e.fret, e.technique.kind if e.technique else None)
        for e in summary.scores[0].events
    ]
    # Bends come from the transcribed Note.bends (QuantizedNote drops them).
    bend = summary.scores[0].events[0].technique
    assert bend is not None and bend.kind == "bend" and bend.bend_semitones == 2.0
    assert kinds == [(7, "bend"), (5, "hammer_on"), (7, None), (0, None)]
    assert summary.scores[0].events[1].technique.target_fret == 7

    song = guitarpro.parse(str(tmp_path / "fx.gp5"))
    notes = [
        n
        for m in song.tracks[0].measures
        for b in m.voices[0].beats
        for n in b.notes
    ]
    assert notes[0].effect.bend is not None and notes[1].effect.hammer


def test_no_techniques_switch_leaves_events_plain_and_has_its_own_cache(tmp_path):
    write_input(tmp_path)
    on = _run_techniques(tmp_path, tmp_path / "on.gp5")
    off = _run_techniques(tmp_path, tmp_path / "off.gp5", techniques=False)
    assert off.cache_hit is False  # the switch is part of the cache version
    assert any(e.technique for e in on.scores[0].events)
    assert all(e.technique is None for e in off.scores[0].events)
    assert [(e.string, e.fret) for e in off.scores[0].events] == [
        (e.string, e.fret) for e in on.scores[0].events
    ]
    again = _run_techniques(tmp_path, tmp_path / "off2.gp5", techniques=False)
    assert again.cache_hit is True
    assert all(e.technique is None for e in again.scores[0].events)


def test_tablature_version_pins_the_technique_switch():
    configs = pipeline._fretting_configs(
        ["guitar"], {"guitar": resolve_tuning(None, "guitar")}, {}
    )
    on = pipeline.tablature_version(configs)
    off = pipeline.tablature_version(configs, techniques=False)
    assert on != off
    assert off.endswith("+tech-off") and "+tech-" in on
    assert f"+rev-{pipeline.TABLATURE_PIPELINE_REVISION}+" in on


def _gp5_effects(path: Path) -> list[tuple]:
    song = guitarpro.parse(str(path))
    return [
        (n.effect.bend is not None, bool(n.effect.slides), n.effect.hammer)
        for track in song.tracks
        for m in track.measures
        for b in m.voices[0].beats
        for n in b.notes
    ]


def test_cli_no_techniques_writes_no_effect(tmp_path, monkeypatch):
    """`tabgen export --no-techniques` with injected stages: no effect at all
    in the .gp5 (the default run of the same input does carry effects)."""
    from typer.testing import CliRunner

    from tabgen.cli.main import app

    audio = write_input(tmp_path)
    separate, analysis, _ = make_fakes(tmp_path, [])
    real_run = pipeline.run_tablature

    def injected(*args, **kwargs):
        return real_run(
            *args,
            separate_fn=separate,
            analysis_fn=analysis,
            transcribe_fn=_technique_transcribe,
            fretting_fn=_technique_fretting,
            **kwargs,
        )

    monkeypatch.setattr(pipeline, "run_tablature", injected)
    runner = CliRunner()
    plain = tmp_path / "plain.gp5"
    result = runner.invoke(
        app,
        ["export", str(audio), "-o", str(plain), "--instruments", "guitar",
         "--no-techniques"],
    )
    assert result.exit_code == 0, result.output
    effects = _gp5_effects(plain)
    assert effects and not any(any(fx) for fx in effects)

    styled = tmp_path / "styled.gp5"
    result = runner.invoke(
        app, ["export", str(audio), "-o", str(styled), "--instruments", "guitar"]
    )
    assert result.exit_code == 0, result.output
    assert "2 technique(s)" in result.output
    assert any(any(fx) for fx in _gp5_effects(styled))
