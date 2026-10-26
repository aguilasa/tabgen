"""Tests for the transcription pipeline orchestration.

Separation and transcription are injected fakes (no Demucs, no Basic
Pitch model); the MIDI export stage runs for real. The cache test runs
the real separation wrapper with a fake separator factory, so only
ffmpeg actually executes there.
"""

from pathlib import Path

import mido
import numpy as np
import pytest
import soundfile

from tabgen.core import pipeline
from tabgen.core.models import Note, NoteEvents, SeparationResult
from tabgen.core.pipeline import PipelineError, run_transcription
from tabgen.core.transcription.basic_pitch import TranscriptionResult

NOTES_PER_INSTRUMENT = {
    "guitar": [Note(pitch_midi=64, start_s=0.0, end_s=0.5, velocity=0.8)],
    "bass": [
        Note(pitch_midi=28, start_s=0.0, end_s=1.0, velocity=0.9),
        Note(pitch_midi=33, start_s=1.0, end_s=2.0, velocity=0.7),
    ],
}


def write_input(tmp_path: Path, name: str = "song.wav") -> Path:
    """Write a short silent stereo wav as the pipeline input."""
    path = tmp_path / name
    soundfile.write(str(path), np.zeros((4410, 2), dtype=np.float32), 44100)
    return path


def make_fake_separate(tmp_path: Path, calls: list[Path], cache_hit: bool = False):
    """A separate() stand-in that writes stem placeholders and reports pct."""
    stems_dir = tmp_path / "stems"
    stems_dir.mkdir(exist_ok=True)
    stems = {}
    for name in ("guitar", "bass", "drums", "vocals", "other"):
        stem = stems_dir / f"{name}.wav"
        stem.touch()
        stems[name] = str(stem)

    def fake_separate(
        input_path: Path,
        device: str | None = None,
        on_progress: pipeline.ProgressCallback = pipeline.null_progress,
    ):
        calls.append(Path(input_path))
        on_progress("separation", 0.0)
        on_progress("separation", 50.0)
        on_progress("separation", 100.0)
        return SeparationResult(stems=stems, model_version="fake"), cache_hit

    return fake_separate


def make_fake_transcribe(calls: list[tuple[Path, str]]):
    """A transcribe() stand-in returning canned notes per instrument."""

    def fake_transcribe(
        input_path: Path,
        instrument: str = "guitar",
        on_progress: pipeline.ProgressCallback = pipeline.null_progress,
    ):
        calls.append((Path(input_path), instrument))
        on_progress("transcription", 0.0)
        on_progress("transcription", 100.0)
        notes = list(NOTES_PER_INSTRUMENT[instrument])
        events = NoteEvents(notes=notes, instrument=instrument, model_version="fake")
        return TranscriptionResult(note_events=events, bends=[None] * len(notes)), False

    return fake_transcribe


def test_orchestration_routes_stems_and_writes_midi_per_instrument(
    tmp_path: Path,
) -> None:
    sample = write_input(tmp_path)
    separate_calls: list[Path] = []
    transcribe_calls: list[tuple[Path, str]] = []

    summary = run_transcription(
        sample,
        instruments=("guitar", "bass"),
        separate_fn=make_fake_separate(tmp_path, separate_calls),
        transcribe_fn=make_fake_transcribe(transcribe_calls),
    )

    assert separate_calls == [sample]
    # Each instrument is transcribed from its own stem.
    assert transcribe_calls == [
        (tmp_path / "stems" / "guitar.wav", "guitar"),
        (tmp_path / "stems" / "bass.wav", "bass"),
    ]
    assert not summary.separation_cache_hit
    assert [(i.instrument, i.note_count) for i in summary.instruments] == [
        ("guitar", 1),
        ("bass", 2),
    ]
    # MIDI files land next to the input, named <input-stem>.<instrument>.mid.
    for item in summary.instruments:
        midi_path = Path(item.midi_path)
        assert midi_path == tmp_path / f"song.{item.instrument}.mid"
        mid = mido.MidiFile(midi_path)  # reopens without error
        note_ons = [
            msg
            for track in mid.tracks
            for msg in track
            if msg.type == "note_on" and msg.velocity > 0
        ]
        assert len(note_ons) == item.note_count


def test_output_dir_option_redirects_the_midi_files(tmp_path: Path) -> None:
    sample = write_input(tmp_path)
    out_dir = tmp_path / "out" / "midi"  # does not exist yet

    summary = run_transcription(
        sample,
        instruments=("guitar",),
        output_dir=out_dir,
        separate_fn=make_fake_separate(tmp_path, []),
        transcribe_fn=make_fake_transcribe([]),
    )

    (item,) = summary.instruments
    assert Path(item.midi_path) == out_dir / "song.guitar.mid"
    assert (out_dir / "song.guitar.mid").is_file()


def test_progress_reports_each_stage_in_order_up_to_100(tmp_path: Path) -> None:
    sample = write_input(tmp_path)
    events: list[tuple[str, float]] = []

    run_transcription(
        sample,
        instruments=("guitar", "bass"),
        on_progress=lambda stage, pct: events.append((stage, pct)),
        separate_fn=make_fake_separate(tmp_path, []),
        transcribe_fn=make_fake_transcribe([]),
    )

    stages = [stage for stage, _ in events]
    expected_order = [
        "separation",
        "transcription:guitar",
        "export:guitar",
        "transcription:bass",
        "export:bass",
    ]
    # Every expected stage appears, grouped and in pipeline order.
    assert [s for i, s in enumerate(stages) if i == 0 or stages[i - 1] != s] == (
        expected_order
    )
    # Each stage ends at 100.0 and never leaves [0, 100].
    for name in expected_order:
        stage_pcts = [pct for stage, pct in events if stage == name]
        assert stage_pcts[-1] == 100.0
    assert all(0.0 <= pct <= 100.0 for _, pct in events)


def test_warm_separation_cache_skips_demucs_on_second_run(tmp_path: Path) -> None:
    """Real separation wrapper + counting fake Demucs: cache means no rerun."""
    import torch

    from tabgen.core.separation import demucs as demucs_core

    class FakeSeparator:
        samplerate = 44100
        _sources = ("vocals", "drums", "bass", "other", "guitar")

        def separate_audio_file(self, file: Path):
            stems = {name: torch.zeros(2, 4410) for name in self._sources}
            return torch.zeros(2, 4410), stems

    sample = write_input(tmp_path)
    model_runs: list[str] = []

    def factory(model: str, device: str, segment: int, callback):
        model_runs.append(model)
        return FakeSeparator()

    def separate_fn(
        input_path: Path,
        device: str | None = None,
        on_progress: pipeline.ProgressCallback = pipeline.null_progress,
    ):
        return demucs_core.separate(
            input_path,
            device="cpu",
            on_progress=on_progress,
            separator_factory=factory,
        )

    first = run_transcription(
        sample,
        instruments=("guitar",),
        separate_fn=separate_fn,
        transcribe_fn=make_fake_transcribe([]),
    )
    assert not first.separation_cache_hit
    assert len(model_runs) == 2  # both Demucs models ran once

    second = run_transcription(
        sample,
        instruments=("guitar",),
        separate_fn=separate_fn,
        transcribe_fn=make_fake_transcribe([]),
    )
    assert second.separation_cache_hit
    assert len(model_runs) == 2  # Demucs did not run again


def test_missing_stem_for_requested_instrument_raises(tmp_path: Path) -> None:
    sample = write_input(tmp_path)

    def separate_fn(input_path, device=None, on_progress=pipeline.null_progress):
        return SeparationResult(stems={"guitar": "g.wav"}), False

    with pytest.raises(PipelineError, match="bass"):
        run_transcription(
            sample,
            instruments=("bass",),
            separate_fn=separate_fn,
            transcribe_fn=make_fake_transcribe([]),
        )


def test_empty_instrument_list_raises(tmp_path: Path) -> None:
    sample = write_input(tmp_path)
    with pytest.raises(PipelineError, match="no instruments"):
        run_transcription(sample, instruments=())
