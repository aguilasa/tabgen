"""Tests for the harmony-analysis stage (key + chords).

The triad test runs the real madmom models (CPU) over ~10 s of
synthetic sine triads, which takes a few seconds. The stem-summing and
merge tests use injected fake processors, so no model runs there.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile

from tabgen.core.analysis.harmony import (
    STAGE,
    HarmonyError,
    analyze_harmony,
    merge_consecutive_segments,
    sum_harmonic_stems,
)

SR = 44100

# Triads as (root, third, fifth) fundamentals in Hz.
A_MIN = (220.0, 261.63, 329.63)
C_MAJ = (261.63, 329.63, 392.0)
F_MAJ = (174.61, 220.0, 261.63)
G_MAJ = (196.0, 246.94, 293.66)


def _triad(freqs: tuple[float, ...], duration_s: float) -> np.ndarray:
    """One sustained sine triad with a few harmonics and click-free edges."""
    t = np.arange(int(SR * duration_s)) / SR
    wave = np.zeros_like(t)
    for freq in freqs:
        for k, amp in enumerate((1.0, 0.5, 0.33, 0.25), start=1):
            wave += 0.2 * amp * np.sin(2 * np.pi * freq * k * t)
    fade = int(0.01 * SR)
    wave[:fade] *= np.linspace(0.0, 1.0, fade)
    wave[-fade:] *= np.linspace(1.0, 0.0, fade)
    return wave


def _write_wav(path: Path, wave: np.ndarray) -> str:
    peak = np.abs(wave).max()
    if peak > 0.99:
        wave = wave / peak * 0.99
    soundfile.write(str(path), wave.astype(np.float32), SR)
    return str(path)


def _contains_in_order(labels: list[str], expected: tuple[str, ...]) -> bool:
    """True when ``expected`` is a subsequence of ``labels``."""
    labels_iter = iter(labels)
    return all(any(label == want for label in labels_iter) for want in expected)


def test_real_madmom_detects_triad_progression_and_key(tmp_path: Path) -> None:
    # vi-I-IV-V-I in C major: contains A:min, C:maj, G:maj in order and
    # the F->G->C cadence anchors the key (A:min/C:maj/G:maj alone reads
    # as ii-IV-I in G major to the key CNN).
    wave = np.concatenate(
        [_triad(chord, 2.0) for chord in (A_MIN, C_MAJ, F_MAJ, G_MAJ, C_MAJ)]
    )
    stem = _write_wav(tmp_path / "other.wav", wave)

    result = analyze_harmony({"other": stem})

    labels = [c.label for c in result.chords if c.label != "N"]
    assert _contains_in_order(labels, ("A:min", "C:maj", "G:maj")), labels
    assert result.key in ("A minor", "C major"), result.key
    assert 0.0 < result.key_confidence <= 1.0
    for segment in result.chords:
        assert segment.end_s > segment.start_s


def test_sum_harmonic_stems_excludes_drums_and_pads(tmp_path: Path) -> None:
    def write_const(name: str, value: float, samples: int) -> str:
        path = tmp_path / f"{name}.wav"
        soundfile.write(str(path), np.full(samples, value, dtype=np.float32), SR)
        return str(path)

    stems = {
        "guitar": write_const("guitar", 0.2, 1000),
        "bass": write_const("bass", 0.1, 500),  # shorter: must be zero-padded
        "drums": write_const("drums", 0.5, 1000),
    }

    mix, sample_rate = sum_harmonic_stems(stems)

    assert sample_rate == SR
    assert len(mix) == 1000
    # guitar + bass where both exist, guitar alone afterwards; never drums.
    assert np.allclose(mix[:500], 0.3, atol=1e-3)
    assert np.allclose(mix[500:], 0.2, atol=1e-3)


def test_sum_harmonic_stems_requires_non_drums_stem(tmp_path: Path) -> None:
    path = tmp_path / "drums.wav"
    soundfile.write(str(path), np.zeros(100, dtype=np.float32), SR)

    with pytest.raises(HarmonyError, match="non-drums"):
        sum_harmonic_stems({"drums": str(path)})


def test_merge_consecutive_segments_merges_equal_labels() -> None:
    merged = merge_consecutive_segments(
        [
            (0.0, 1.0, "A:min"),
            (1.0, 2.0, "A:min"),
            (2.0, 3.0, "C:maj"),
            (3.0, 3.5, "N"),
            (3.5, 4.0, "C:maj"),
            (4.0, 5.0, "C:maj"),
        ]
    )

    assert [(s.start_s, s.end_s, s.label) for s in merged] == [
        (0.0, 2.0, "A:min"),
        (2.0, 3.0, "C:maj"),
        (3.0, 3.5, "N"),
        (3.5, 5.0, "C:maj"),
    ]


def test_analyze_harmony_with_injected_processors(tmp_path: Path) -> None:
    def write_const(name: str, value: float) -> str:
        path = tmp_path / f"{name}.wav"
        soundfile.write(str(path), np.full(800, value, dtype=np.float32), SR)
        return str(path)

    stems = {
        "guitar": write_const("guitar", 0.2),
        "other": write_const("other", 0.1),
        "drums": write_const("drums", 0.5),
    }
    seen_mixes: list[np.ndarray] = []

    def fake_key_processor(path: str) -> np.ndarray:
        mix, _ = soundfile.read(path)
        seen_mixes.append(mix)
        prediction = np.zeros((1, 24))
        prediction[0, 12] = 0.9  # madmom key class 12 is "A minor"
        return prediction

    def fake_feature_processor(path: str) -> str:
        assert Path(path).is_file()
        return "features-sentinel"

    def fake_decoder(features: str) -> list[tuple[float, float, str]]:
        assert features == "features-sentinel"
        return [(0.0, 1.0, "A:min"), (1.0, 2.0, "A:min"), (2.0, 3.0, "C:maj")]

    progress: list[tuple[str, float]] = []

    result = analyze_harmony(
        stems,
        on_progress=lambda stage, pct: progress.append((stage, pct)),
        key_processor=fake_key_processor,
        chord_feature_processor=fake_feature_processor,
        chord_decoder=fake_decoder,
    )

    # The mix the processor received sums guitar + other only (no drums).
    assert np.allclose(seen_mixes[0], 0.3, atol=1e-3)
    assert result.key == "A minor"
    assert result.key_confidence == pytest.approx(0.9)
    assert [(s.start_s, s.end_s, s.label) for s in result.chords] == [
        (0.0, 2.0, "A:min"),
        (2.0, 3.0, "C:maj"),
    ]
    assert progress[0] == (STAGE, 0.0)
    assert progress[-1] == (STAGE, 100.0)
