"""Tests for the Basic Pitch transcription stage.

The pitch-detection tests run the real model (ONNX backend) on short
synthetic sines — CPU inference on ~1 s of audio takes a few seconds.
The cache/progress/bends tests use a counting fake predictor instead,
so no model runs there.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile

from tabgen.core.transcription import basic_pitch as bp

SR = 22050


def write_tone(
    path: Path, partials: list[tuple[float, float]], duration_s: float = 1.0
) -> Path:
    """Write a mono wav made of (frequency_hz, amplitude) sine partials."""
    t = np.arange(int(SR * duration_s)) / SR
    wave = np.zeros_like(t)
    for freq, amp in partials:
        wave += amp * np.sin(2 * np.pi * freq * t)
    soundfile.write(str(path), wave.astype(np.float32), SR)
    return path


def test_a4_sine_maps_to_midi_69_with_accurate_onset(tmp_path: Path) -> None:
    sample = write_tone(tmp_path / "a4.wav", [(440.0, 0.5)], duration_s=1.0)

    result, cache_hit = bp.transcribe(sample, instrument="guitar")

    assert not cache_hit
    events = result.note_events
    assert events.instrument == "guitar"
    assert events.model_version == bp.MODEL_VERSION
    pitches = [note.pitch_midi for note in events.notes]
    assert 69 in pitches
    a4 = next(note for note in events.notes if note.pitch_midi == 69)
    assert abs(a4.start_s - 0.0) < 0.2  # onset error under 200 ms
    assert a4.end_s > a4.start_s
    assert 0.0 < a4.confidence <= 1.0
    # bends run parallel to notes and the contract stays JSON-serializable.
    assert len(result.bends) == len(events.notes)
    events.to_json()


def test_e1_with_bass_profile_detects_pitch_28_not_octave_up(
    tmp_path: Path,
) -> None:
    # E1 fundamental (41.2 Hz) plus two harmonics, as a plucked bass has.
    e1 = 41.203
    sample = write_tone(
        tmp_path / "e1.wav",
        [(e1, 0.5), (2 * e1, 0.25), (3 * e1, 0.12)],
        duration_s=1.5,
    )

    result, _ = bp.transcribe(sample, instrument="bass")

    pitches = [note.pitch_midi for note in result.note_events.notes]
    assert 28 in pitches  # true E1
    assert 40 not in pitches  # no octave jump to E2
    assert result.note_events.instrument == "bass"


def make_counting_predictor(calls: list[Path]) -> bp.Predictor:
    """A fake predictor returning fixed raw events and counting its runs."""

    def predictor(
        audio_path: Path, profile: bp.InstrumentProfile
    ) -> list[bp.RawNoteEvent]:
        calls.append(audio_path)
        return [
            (0.5, 1.0, 45, 0.8, [0, 1, 2]),
            (0.0, 0.4, 33, 0.9, None),
        ]

    return predictor


def test_second_call_is_a_cache_hit_without_model_rerun(tmp_path: Path) -> None:
    sample = write_tone(tmp_path / "stem.wav", [(110.0, 0.5)])
    calls: list[Path] = []
    predictor = make_counting_predictor(calls)

    first, first_hit = bp.transcribe(sample, instrument="bass", predictor=predictor)
    assert not first_hit
    assert len(calls) == 1

    progress: list[float] = []
    second, second_hit = bp.transcribe(
        sample,
        instrument="bass",
        predictor=predictor,
        on_progress=lambda stage, pct: progress.append(pct),
    )

    assert second_hit
    assert len(calls) == 1  # the model did not run again
    assert second == first
    assert progress == [100.0]
    # Notes are sorted by onset; numpy-free builtins; bends preserved.
    assert [note.pitch_midi for note in second.note_events.notes] == [33, 45]
    assert second.bends == [None, [0, 1, 2]]


def test_instrument_is_part_of_the_cache_key(tmp_path: Path) -> None:
    sample = write_tone(tmp_path / "stem.wav", [(110.0, 0.5)])
    calls: list[Path] = []
    predictor = make_counting_predictor(calls)

    _, guitar_hit = bp.transcribe(sample, instrument="guitar", predictor=predictor)
    _, bass_hit = bp.transcribe(sample, instrument="bass", predictor=predictor)

    assert not guitar_hit
    assert not bass_hit
    assert len(calls) == 2  # different instruments never share an entry


def test_unknown_instrument_raises(tmp_path: Path) -> None:
    sample = write_tone(tmp_path / "stem.wav", [(110.0, 0.5)])
    with pytest.raises(bp.TranscriptionError, match="unknown instrument"):
        bp.transcribe(sample, instrument="banjo")


def test_missing_input_raises(tmp_path: Path) -> None:
    with pytest.raises(bp.TranscriptionError, match="not found"):
        bp.transcribe(tmp_path / "nope.wav")
