"""Riley guitar transcription (hybrid with Basic Pitch bends), offline.

No network and no real weights: the model is a fake torch module or a fake
predictor, and Basic Pitch is a fake transcription carrying bend curves.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile
import torch

from tabgen.core import pipeline
from tabgen.core.cache import StageCache
from tabgen.core.models import (
    AnalysisResult,
    Note,
    NoteEvents,
    SeparationResult,
)
from tabgen.core.pipeline import AnalysisSummary, run_tablature
from tabgen.core.transcription import basic_pitch, riley
from tabgen.core.transcription.basic_pitch import (
    TranscriptionError,
    TranscriptionResult,
)

SHA_PREFIX = riley.WEIGHTS_SHA256[:12]
# Basic Pitch bend bins are 1/3 semitone: 6 bins = a whole step held ~0.38 s.
WHOLE_STEP_BEND = [0] * 6 + [6] * 33


def write_wav(path: Path, seconds: float = 0.1) -> Path:
    soundfile.write(str(path), np.zeros(int(44100 * seconds), dtype=np.float32), 44100)
    return path


def fake_bend_transcribe(notes: list[Note]):
    calls: list[str] = []

    def transcribe(input_path, instrument="guitar", on_progress=None, cache=None):
        calls.append(instrument)
        events = NoteEvents(notes=[Note(**vars(n)) for n in notes],
                            instrument=instrument,
                            model_version=basic_pitch.MODEL_VERSION)
        return TranscriptionResult(note_events=events), False

    transcribe.calls = calls
    return transcribe


def test_riley_note_events_carry_the_weights_sha(tmp_path):
    stem = write_wav(tmp_path / "guitar.wav")
    bp = fake_bend_transcribe([])
    calls: list[Path] = []

    def predictor(path):
        calls.append(path)
        return [(0.5, 0.9, 60, 0.8), (1.0, 1.0, 62, 0.5)]  # 2nd: zero length

    result, hit = riley.transcribe(stem, predictor=predictor, bend_transcribe=bp)
    assert hit is False
    events = result.note_events
    assert SHA_PREFIX in events.model_version
    assert events.model_version == riley.MODEL_VERSION
    assert SHA_PREFIX in riley.transcription_version("guitar")
    assert [(n.pitch_midi, n.start_s, n.end_s) for n in events.notes] == [
        (60, 0.5, 0.9)
    ]
    assert bp.calls == ["guitar"]

    again, hit = riley.transcribe(stem, predictor=predictor, bend_transcribe=bp)
    assert hit is True and len(calls) == 1
    assert again.note_events.model_version == riley.MODEL_VERSION
    assert StageCache(stem).get("transcription", riley.transcription_version())


def test_riley_rejects_the_bass(tmp_path):
    stem = write_wav(tmp_path / "bass.wav")
    with pytest.raises(TranscriptionError):
        riley.transcribe(stem, instrument="bass", predictor=lambda p: [])


def test_merge_copies_bends_only_to_matched_notes():
    tol = riley.BEND_MATCH_TOLERANCE_S
    notes = [
        Note(pitch_midi=60, start_s=1.0, end_s=1.4),  # matched (+30 ms)
        Note(pitch_midi=62, start_s=2.0, end_s=2.4),  # BP onset too late
        Note(pitch_midi=64, start_s=3.0, end_s=3.4),  # BP pitch differs
        Note(pitch_midi=67, start_s=4.0, end_s=4.4),  # no BP note at all
        Note(pitch_midi=60, start_s=1.02, end_s=1.3),  # loses the BP note
    ]
    notes[3].bends = [9, 9]  # stale bends never survive the merge
    bp = [
        Note(pitch_midi=60, start_s=1.03, end_s=1.5, bends=[1, 2, 3]),
        Note(pitch_midi=62, start_s=2.0 + tol + 0.01, end_s=2.5, bends=[4]),
        Note(pitch_midi=65, start_s=3.0, end_s=3.5, bends=[5]),
    ]
    merged = riley.merge_bends(notes, bp)
    assert [n.bends for n in merged] == [None, None, None, None, [1, 2, 3]]
    # Nearest onset wins the one-to-one match (1.02 is closer to 1.03).
    assert merged[4].bends is not bp[0].bends  # copied, not shared

    exact = [Note(pitch_midi=62, start_s=2.0, end_s=2.4)]
    at_tolerance = [Note(pitch_midi=62, start_s=2.0 + tol, end_s=2.5, bends=[7])]
    assert riley.merge_bends(exact, at_tolerance)[0].bends == [7]


class _FakeCRNN(torch.nn.Module):
    """Stands in for the CRNN: one C4 note, onset at frame 100 (1.00 s),
    frame activity until frame 150, velocity 0.8."""

    def __init__(self):
        super().__init__()
        self.dummy = torch.nn.Parameter(torch.zeros(1))

    def forward(self, waveform):
        batch = waveform.shape[0]
        frames = waveform.shape[1] // (riley.SAMPLE_RATE // riley.FRAMES_PER_SECOND) + 1
        shape = (batch, frames, riley.CLASSES_NUM)
        onset = torch.zeros(shape)
        frame = torch.zeros(shape)
        k = 60 - riley.BEGIN_NOTE
        onset[:, 98:103, k] = torch.tensor([0.2, 0.5, 1.0, 0.5, 0.2])
        frame[:, 100:151, k] = 0.9
        return {
            "reg_onset_output": onset,
            "reg_offset_output": torch.zeros(shape),
            "frame_output": frame,
            "velocity_output": torch.full(shape, 0.8),
        }


def test_fake_network_output_is_post_processed_into_notes():
    audio = np.zeros(3 * riley.SAMPLE_RATE, dtype=np.float32)
    outputs = riley.frame_outputs(_FakeCRNN(), audio)
    assert outputs["frame_output"].shape == (1001, riley.CLASSES_NUM)
    notes = riley.outputs_to_notes(outputs)
    assert len(notes) == 1
    onset, offset, pitch, velocity = notes[0]
    assert pitch == 60
    assert onset == pytest.approx(1.00, abs=1e-6)
    assert offset == pytest.approx(1.51, abs=1e-6)  # frame 151 drops below 0.1
    assert velocity == pytest.approx(0.8, abs=1e-6)


def test_weights_with_a_wrong_sha_are_refused(tmp_path):
    bogus = tmp_path / "guitar-gaps.pth"
    bogus.write_bytes(b"not the pinned checkpoint")
    with pytest.raises(TranscriptionError, match="sha256"):
        riley.weights_path(download=lambda: bogus)


def test_tablature_version_pins_transcriber_and_weights_sha():
    configs = pipeline._fretting_configs(
        ["guitar", "bass"],
        {"guitar": pipeline.resolve_tuning(None, "guitar"),
         "bass": pipeline.resolve_tuning(None, "bass")},
        {},
    )
    plain = pipeline.tablature_version(configs, transcriber="basic-pitch")
    assert "riley" not in plain  # basic-pitch keeps its pre-REF-TASK-09 key
    with_riley = pipeline.tablature_version(configs, transcriber="riley")
    tag = pipeline.transcriber_tag("riley", ["guitar"])
    assert tag.startswith(f"+riley-{riley.WEIGHTS_SHA256[:8]}-")
    assert tag in with_riley and with_riley.replace(tag, "") == plain
    # The default (riley since REF-TASK-09) is the riley key.
    assert pipeline.DEFAULT_TRANSCRIBER == "riley"
    assert pipeline.tablature_version(configs) == with_riley
    bass_only = pipeline._fretting_configs(
        ["bass"], {"bass": pipeline.resolve_tuning(None, "bass")}, {}
    )
    assert pipeline.tablature_version(
        bass_only, transcriber="riley"
    ) == pipeline.tablature_version(bass_only, transcriber="basic-pitch")
    with pytest.raises(pipeline.PipelineError):
        pipeline.tablature_version(configs, transcriber="nope")


# --------------------------------------------------------------------------
# End to end through run_tablature(transcriber="riley") with fake stages.

BEATS = [0.5 + 0.5 * i for i in range(9)]
DOWNBEATS = BEATS[::4]


def _fake_stages(tmp_path: Path):
    stems_dir = tmp_path / "stems"
    stems_dir.mkdir()
    stems = {}
    for name in ("guitar", "bass", "drums", "vocals", "other"):
        stems[name] = str(write_wav(stems_dir / f"{name}.wav"))

    def separate(input_path, device=None, on_progress=pipeline.null_progress):
        return SeparationResult(stems=stems, model_version="fake"), True

    def analysis(input_path, device=None, on_progress=pipeline.null_progress,
                 cache=None):
        return AnalysisSummary(
            input_path=str(input_path),
            separation_cache_hit=True,
            analysis_cache_hit=False,
            result=AnalysisResult(tempo_bpm=120.0, beat_times=list(BEATS),
                                  downbeat_times=list(DOWNBEATS), key="A minor",
                                  key_confidence=0.9, chords=[]),
        )

    return separate, analysis


def test_riley_note_with_matched_bend_comes_out_as_bend_technique(
    tmp_path, monkeypatch
):
    song = write_wav(tmp_path / "song.wav")
    separate, analysis = _fake_stages(tmp_path)
    # Riley: D4 at 0.5 s (bent in Basic Pitch) and E4 at 2.0 s (no bend).
    monkeypatch.setattr(
        riley, "predict",
        lambda path, device=None: [(0.5, 0.95, 62, 0.9), (2.0, 2.45, 64, 0.9)],
    )
    # Basic Pitch: the same D4 22 ms later with a whole-step bend, plus a
    # spurious bent note Riley did not report.
    bp = fake_bend_transcribe([
        Note(pitch_midi=62, start_s=0.522, end_s=0.9, bends=list(WHOLE_STEP_BEND)),
        Note(pitch_midi=69, start_s=3.0, end_s=3.4, bends=list(WHOLE_STEP_BEND)),
    ])
    monkeypatch.setattr(basic_pitch, "transcribe", bp)

    summary = run_tablature(
        song,
        output_path=tmp_path / "riley.gp5",
        instruments=["guitar"],
        separate_fn=separate,
        analysis_fn=analysis,
        transcriber="riley",
    )
    events = summary.scores[0].events
    assert len(events) == 2  # notes come from Riley, not from Basic Pitch
    bend = events[0].technique
    assert bend is not None and bend.kind == "bend" and bend.bend_semitones == 2.0
    assert events[1].technique is None
    assert bp.calls == ["guitar"]


def test_cli_rejects_unknown_transcriber(tmp_path):
    from typer.testing import CliRunner

    from tabgen.cli.main import app

    song = write_wav(tmp_path / "song.wav")
    result = CliRunner().invoke(
        app, ["export", str(song), "-o", str(tmp_path / "x.gp5"),
              "--transcriber", "nope"],
    )
    assert result.exit_code == 2
    assert "unknown transcriber" in result.output
