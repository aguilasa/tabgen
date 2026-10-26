"""Tests for the beat/downbeat/tempo analysis stage.

The click-track test runs the real madmom chain (RNN + DBN) on a 12 s
synthetic click track — CPU runtime is ~2 s. It asserts stable facts
only (BPM within tolerance, median downbeat spacing), never exact
segment counts or fine timestamps. The remaining tests inject a fake
processor, so madmom never loads there.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile

from tabgen.core.analysis import BeatAnalysis, BeatAnalysisError, analyze_beats
from tabgen.core.analysis import beats as beats_mod

SR = 44100


def write_click_track(
    path: Path, bpm: float = 120.0, beats_per_bar: int = 4, duration_s: float = 12.0
) -> Path:
    """Write a mono click track: short sine bursts, downbeats accented."""
    period = 60.0 / bpm
    wave = np.zeros(int(SR * duration_s), dtype=np.float32)
    click_len = int(0.010 * SR)
    t = np.arange(click_len) / SR
    envelope = np.exp(-t / 0.002)
    beat = 0
    while True:
        start = int(round(beat * period * SR))
        if start + click_len > wave.size:
            break
        accented = beat % beats_per_bar == 0
        freq = 1500.0 if accented else 1000.0
        amp = 0.9 if accented else 0.4
        wave[start : start + click_len] += (
            amp * np.sin(2 * np.pi * freq * t) * envelope
        ).astype(np.float32)
        beat += 1
    soundfile.write(str(path), wave, SR)
    return path


def test_click_track_120bpm_real_madmom(tmp_path: Path) -> None:
    sample = write_click_track(tmp_path / "click120.wav")

    result = analyze_beats(sample)

    assert 118.0 <= result.tempo_bpm <= 122.0
    # Enough material decoded to make the spacing assertions meaningful.
    assert len(result.beat_times) >= 8
    assert len(result.downbeat_times) >= 3
    # Median inter-beat interval ~0.5 s and downbeats every 4 beats (~2.0 s).
    assert abs(np.median(np.diff(result.beat_times)) - 0.5) < 0.05
    assert abs(np.median(np.diff(result.downbeat_times)) - 2.0) < 0.1
    # Every downbeat is one of the decoded beats.
    assert set(result.downbeat_times) <= set(result.beat_times)


def madmom_shaped(rows: list[tuple[float, float]]) -> np.ndarray:
    """Build madmom's (N, 2) output: [beat time, position in bar]."""
    return np.asarray(rows, dtype=float)


def test_mocked_processor_maps_times_positions_and_bpm(tmp_path: Path) -> None:
    wav = tmp_path / "silence.wav"
    soundfile.write(str(wav), np.zeros(SR, dtype=np.float32), SR)
    # Two 4/4 bars at 120 BPM: beat every 0.5 s, position 1 = downbeat.
    output = madmom_shaped(
        [
            (0.5, 1),
            (1.0, 2),
            (1.5, 3),
            (2.0, 4),
            (2.5, 1),
            (3.0, 2),
            (3.5, 3),
            (4.0, 4),
        ]
    )
    seen_paths: list[Path] = []
    events: list[tuple[str, float]] = []

    def fake_processor(audio_path: Path) -> np.ndarray:
        seen_paths.append(audio_path)
        return output

    result = analyze_beats(
        wav,
        on_progress=lambda stage, pct: events.append((stage, pct)),
        processor=fake_processor,
    )

    assert seen_paths == [wav]
    assert isinstance(result, BeatAnalysis)
    assert result.beat_times == [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    assert result.downbeat_times == [0.5, 2.5]
    assert result.tempo_bpm == pytest.approx(120.0)
    # Plain-float fields: the caller merges them into AnalysisResult,
    # whose contract allows JSON-serializable builtins only.
    assert all(type(t) is float for t in result.beat_times + result.downbeat_times)

    # Progress: single stage, starts at 0, ends at 100, never decreases.
    assert {stage for stage, _ in events} == {beats_mod.STAGE}
    pcts = [pct for _, pct in events]
    assert pcts[0] == 0.0
    assert pcts[-1] == 100.0
    assert pcts == sorted(pcts)


def test_mocked_processor_empty_output_yields_empty_analysis(tmp_path: Path) -> None:
    wav = tmp_path / "silence.wav"
    soundfile.write(str(wav), np.zeros(SR, dtype=np.float32), SR)
    events: list[tuple[str, float]] = []

    result = analyze_beats(
        wav,
        on_progress=lambda stage, pct: events.append((stage, pct)),
        processor=lambda _path: np.empty((0, 2)),
    )

    assert result == BeatAnalysis(tempo_bpm=0.0, beat_times=[], downbeat_times=[])
    assert events[0][1] == 0.0
    assert events[-1][1] == 100.0


def test_single_beat_gives_zero_bpm(tmp_path: Path) -> None:
    wav = tmp_path / "silence.wav"
    soundfile.write(str(wav), np.zeros(SR, dtype=np.float32), SR)

    result = analyze_beats(wav, processor=lambda _p: madmom_shaped([(1.0, 1)]))

    assert result.tempo_bpm == 0.0
    assert result.beat_times == [1.0]
    assert result.downbeat_times == [1.0]


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(BeatAnalysisError, match="not found"):
        analyze_beats(tmp_path / "nope.wav", processor=lambda _p: np.empty((0, 2)))


def test_bad_processor_shape_raises(tmp_path: Path) -> None:
    wav = tmp_path / "silence.wav"
    soundfile.write(str(wav), np.zeros(SR, dtype=np.float32), SR)

    with pytest.raises(BeatAnalysisError, match="expected \\(N, 2\\)"):
        analyze_beats(wav, processor=lambda _p: np.ones((3, 4)))
