"""Beat, downbeat and tempo analysis built on madmom's DBNDownBeatTracker.

The default processor chains :class:`madmom.features.downbeats.
RNNDownBeatProcessor` (frame-wise beat/downbeat activations) with
:class:`~madmom.features.downbeats.DBNDownBeatTrackingProcessor`
(``beats_per_bar=[3, 4]``), which jointly decodes beat times and their
position inside the bar. madmom imports are kept inside the function
because they are slow (scipy/cython extensions).

Tempo is derived from the decoded beats as ``60 / median(inter-beat
interval)``: the median is robust to a single dropped or doubled beat.

The processor is injectable so tests can exercise the mapping logic on a
synthetic madmom-shaped array without running the neural network.

This module is pure core: no stdout/typer/rich. Progress is reported
through the :data:`~tabgen.core.pipeline.ProgressCallback` contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from tabgen.core.pipeline import ProgressCallback, null_progress

STAGE = "analysis:beats"

# Time signatures the DBN decodes over; it picks the best fit per piece.
BEATS_PER_BAR: tuple[int, ...] = (3, 4)

# Frame rate of the RNN activations; the DBN must be told the same value.
FPS = 100

# Maps an audio file to madmom's downbeat output: a float array of shape
# (N, 2) with column 0 = beat time in seconds (ascending) and column 1 =
# beat position inside the bar (1 = downbeat, up to beats_per_bar).
BeatProcessor = Callable[[Path], np.ndarray]


class BeatAnalysisError(RuntimeError):
    """Raised when the beat-analysis stage cannot run."""


@dataclass
class BeatAnalysis:
    """Rhythm fields of :class:`~tabgen.core.models.AnalysisResult`.

    A partial result on purpose: key/chords belong to other analysis
    stages, so the caller merges these fields into the full
    ``AnalysisResult`` instead of this stage inventing placeholders.
    """

    tempo_bpm: float = 0.0
    beat_times: list[float] = field(default_factory=list)
    downbeat_times: list[float] = field(default_factory=list)


def _run_madmom(audio_path: Path) -> np.ndarray:
    """Default :data:`BeatProcessor`: RNN activations + DBN decoding."""
    # Lazy: importing madmom pulls in scipy and compiled extensions.
    from madmom.features.downbeats import (
        DBNDownBeatTrackingProcessor,
        RNNDownBeatProcessor,
    )

    activations = RNNDownBeatProcessor()(str(audio_path))
    tracker = DBNDownBeatTrackingProcessor(beats_per_bar=list(BEATS_PER_BAR), fps=FPS)
    return np.asarray(tracker(activations))


def _tempo_from_beats(beat_times: np.ndarray) -> float:
    """BPM as 60 / median inter-beat interval; 0.0 when undecidable."""
    if beat_times.size < 2:
        return 0.0
    median_interval = float(np.median(np.diff(beat_times)))
    if median_interval <= 0.0:
        return 0.0
    return 60.0 / median_interval


def analyze_beats(
    audio_path: str | Path,
    on_progress: ProgressCallback = null_progress,
    processor: BeatProcessor | None = None,
) -> BeatAnalysis:
    """Detect beats, downbeats and tempo of ``audio_path``.

    Returns a :class:`BeatAnalysis` whose fields map 1:1 onto the rhythm
    fields of ``AnalysisResult``. Progress is reported on stage
    ``analysis:beats`` from 0.0 to 100.0. ``processor`` defaults to the
    real madmom chain and exists for dependency injection in tests.
    """
    audio_path = Path(audio_path)
    if not audio_path.is_file():
        raise BeatAnalysisError(f"audio file not found: {audio_path}")

    on_progress(STAGE, 0.0)
    if processor is None:
        processor = _run_madmom

    beats = np.asarray(processor(audio_path), dtype=float)
    on_progress(STAGE, 90.0)

    if beats.size == 0:
        on_progress(STAGE, 100.0)
        return BeatAnalysis()
    if beats.ndim != 2 or beats.shape[1] != 2:
        raise BeatAnalysisError(
            f"processor returned shape {beats.shape}; expected (N, 2) "
            "[time, beat position]"
        )

    beat_times = beats[:, 0]
    positions = np.rint(beats[:, 1]).astype(int)
    downbeat_times = beat_times[positions == 1]

    result = BeatAnalysis(
        tempo_bpm=_tempo_from_beats(beat_times),
        beat_times=[float(t) for t in beat_times],
        downbeat_times=[float(t) for t in downbeat_times],
    )
    on_progress(STAGE, 100.0)
    return result
