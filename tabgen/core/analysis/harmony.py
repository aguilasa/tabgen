"""Harmony analysis: global key and chord segments via madmom.

The stage receives the separation stems (name -> wav path), sums every
non-drums stem into a mono "harmonic mix" (percussion only hurts the
tonal models) and runs two madmom pipelines over it:

- key: ``CNNKeyRecognitionProcessor`` (Korzeniowski & Widmer, ISMIR
  2018) yields 24 class probabilities; madmom's own labels are already
  in the contract's ``"<tonic> <mode>"`` form (e.g. ``"A minor"``) and
  the winning probability becomes ``key_confidence``.
- chords: ``CNNChordFeatureProcessor`` -> ``CRFChordRecognitionProcessor``
  (Korzeniowski & Widmer, MLSP 2016) yields (start, end, label) rows
  with Harte-style major/minor labels (``"A:min"``, ``"C:maj"``, ``"N"``),
  converted to :class:`~tabgen.core.models.ChordSegment` with consecutive
  equal labels merged.

madmom imports are lazy and the processors are injectable for tests.
This module is pure core: no print/typer/rich. Progress is reported
through the :data:`~tabgen.core.pipeline.ProgressCallback` contract.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import soundfile

from tabgen.core.models import ChordSegment
from tabgen.core.pipeline import ProgressCallback, null_progress

STAGE = "analysis:harmony"

# Stem names excluded from the harmonic mix (matched case-insensitively).
DRUM_STEM_NAMES = frozenset({"drums"})

# Written wavs stay below full scale so integer re-encoders cannot clip.
_PEAK_LIMIT = 0.99

# Returns the (1, 24) key-class probability array for an audio file.
KeyProcessor = Callable[[str], Any]
# Returns the learned chord features for an audio file.
ChordFeatureProcessor = Callable[[str], Any]
# Decodes chord features into (start_s, end_s, label) rows.
ChordDecoder = Callable[[Any], Sequence[Any]]


class HarmonyError(RuntimeError):
    """Raised when the harmony-analysis stage cannot run."""


@dataclass
class HarmonyResult:
    """Key and chord estimates for one harmonic mix."""

    # Global key as "<tonic> <mode>", e.g. "A minor".
    key: str = ""
    # Probability of the winning key class, in [0.0, 1.0].
    key_confidence: float = 0.0
    chords: list[ChordSegment] = field(default_factory=list)


def sum_harmonic_stems(stems: Mapping[str, str]) -> tuple[np.ndarray, int]:
    """Sum every non-drums stem into a mono float32 mix.

    Stems are downmixed to mono, zero-padded to the longest one and
    added; the result is rescaled when its peak exceeds ``_PEAK_LIMIT``.
    Returns ``(mix, sample_rate)``.
    """
    harmonic = {
        name: path
        for name, path in stems.items()
        if name.lower() not in DRUM_STEM_NAMES
    }
    if not harmonic:
        available = ", ".join(sorted(stems)) or "none"
        raise HarmonyError(
            f"no harmonic (non-drums) stems to analyze; available: {available}"
        )

    mix: np.ndarray | None = None
    sample_rate: int | None = None
    for name in sorted(harmonic):
        path = Path(harmonic[name])
        if not path.is_file():
            raise HarmonyError(f"stem audio not found: {name} -> {path}")
        data, rate = soundfile.read(str(path), dtype="float64", always_2d=True)
        if sample_rate is None:
            sample_rate = int(rate)
        elif int(rate) != sample_rate:
            raise HarmonyError(
                f"stem sample rates differ: {name} has {rate} Hz, "
                f"expected {sample_rate} Hz"
            )
        mono = data.mean(axis=1)
        if mix is None:
            mix = mono
        else:
            if len(mono) > len(mix):
                mix, mono = mono, mix
            mix[: len(mono)] += mono

    assert mix is not None and sample_rate is not None  # guarded above
    peak = float(np.abs(mix).max()) if mix.size else 0.0
    if peak > _PEAK_LIMIT:
        mix = mix * (_PEAK_LIMIT / peak)
    return mix.astype(np.float32), sample_rate


def merge_consecutive_segments(segments: Sequence[Any]) -> list[ChordSegment]:
    """Convert (start, end, label) rows, merging consecutive equal labels.

    Rows may be madmom structured-array records or plain tuples; only
    positional access is used. Each run of equal consecutive labels
    collapses into one segment spanning from the first start to the
    last end.
    """
    merged: list[ChordSegment] = []
    for row in segments:
        start_s, end_s, label = float(row[0]), float(row[1]), str(row[2])
        if merged and merged[-1].label == label:
            merged[-1].end_s = end_s
        else:
            merged.append(ChordSegment(start_s=start_s, end_s=end_s, label=label))
    return merged


def _key_from_prediction(prediction: Any) -> tuple[str, float]:
    """Map a key-class probability array to ("<tonic> <mode>", confidence)."""
    from madmom.features.key import key_prediction_to_label

    probabilities = np.atleast_2d(np.asarray(prediction, dtype=float))
    # madmom's labels are already "<tonic> <mode>" (e.g. "A minor").
    label = str(key_prediction_to_label(probabilities))
    confidence = float(probabilities[0].max())
    return label, confidence


def analyze_harmony(
    stems: Mapping[str, str],
    on_progress: ProgressCallback = null_progress,
    key_processor: KeyProcessor | None = None,
    chord_feature_processor: ChordFeatureProcessor | None = None,
    chord_decoder: ChordDecoder | None = None,
) -> HarmonyResult:
    """Estimate global key and chord segments from separation stems.

    ``stems`` is the :attr:`~tabgen.core.models.SeparationResult.stems`
    mapping; every stem except drums is summed into a temporary mono wav
    that both madmom pipelines consume. The three processor arguments
    default to the real madmom processors (built lazily: loading their
    models takes a moment) and exist for dependency injection in tests.
    """
    on_progress(STAGE, 0.0)
    mix, sample_rate = sum_harmonic_stems(stems)

    with tempfile.TemporaryDirectory(prefix="tabgen-harmony-") as tmp_dir:
        mix_path = str(Path(tmp_dir) / "harmonic_mix.wav")
        soundfile.write(mix_path, mix, sample_rate)
        on_progress(STAGE, 20.0)

        if key_processor is None:
            from madmom.features.key import CNNKeyRecognitionProcessor

            key_processor = CNNKeyRecognitionProcessor()
        key, key_confidence = _key_from_prediction(key_processor(mix_path))
        on_progress(STAGE, 60.0)

        if chord_feature_processor is None:
            from madmom.features.chords import CNNChordFeatureProcessor

            chord_feature_processor = CNNChordFeatureProcessor()
        if chord_decoder is None:
            from madmom.features.chords import CRFChordRecognitionProcessor

            chord_decoder = CRFChordRecognitionProcessor()
        features = chord_feature_processor(mix_path)
        chords = merge_consecutive_segments(chord_decoder(features))

    on_progress(STAGE, 100.0)
    return HarmonyResult(key=key, key_confidence=key_confidence, chords=chords)
