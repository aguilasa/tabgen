"""Quantization stage: project note times onto the beat/downbeat grid.

Each :class:`~tabgen.core.models.Note` onset/offset is snapped to a
subdivision grid laid *between consecutive beats* of the analysis stage, so
variable tempo is respected by construction: the grid follows the actual
``beat_times`` intervals, never a nominal BPM. The result carries a musical
position (measure, beat, subdivision) plus a duration in subdivisions, ready
for the fretting stage to assign string/fret.

Conventions (consumed by the tablature assembly stage):

- ``measure`` and ``beat`` are 1-based; ``subdivision`` is 0-based inside the
  beat, matching :class:`~tabgen.core.models.TabNote`.
- Each beat independently uses either the straight grid
  (``subdivisions_per_beat``, default 4 = sixteenths) or the triplet grid
  (``triplet_subdivisions``, default 3); the triplet grid is chosen when its
  total snap error over the beat's onsets is strictly smaller.
  ``QuantizedNote.subdivisions_in_beat`` records the grid that won.
- Anacrusis: notes before the first downbeat land in measure 0 (counting
  down for earlier virtual measures), with beat numbers continuing backwards
  from the first downbeat (e.g. a one-beat pickup in 4/4 is measure 0,
  beat 4).
- Notes before the first beat or after the last one are placed on a virtual
  grid that extrapolates the first/last inter-beat interval.
- Durations are measured on the note's own beat grid from snapped offset
  minus snapped onset, with a floor of 1 subdivision.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from statistics import median
from typing import Sequence

from tabgen.core.models import Note

# Guards against float noise when flooring beat positions that sit exactly on
# a beat line (e.g. 1.9999999999 must count as beat 2).
_EPS = 1e-9


@dataclass
class QuantizedNote:
    """A note snapped to the beat grid, not yet placed on the fretboard."""

    pitch_midi: int
    # Quantized position (see module docstring for the conventions).
    measure: int
    beat: int
    subdivision: int
    # Grid resolution chosen for this note's beat (e.g. 4 or 3 for triplets).
    subdivisions_in_beat: int
    # Duration in subdivisions of this note's beat grid (>= 1).
    duration_subdivisions: int
    # Original (unquantized) times from the transcription stage, in seconds.
    start_s: float
    end_s: float
    velocity: float = 1.0
    confidence: float = 1.0


def _beat_position(t: float, beats: Sequence[float]) -> float:
    """Continuous position of time ``t`` in beat units.

    The integer part is the 0-based index into ``beats``; the fractional part
    is the position inside that inter-beat interval. Times outside the grid
    extrapolate the first/last interval (positions may be negative).
    """
    if t <= beats[0]:
        return (t - beats[0]) / (beats[1] - beats[0])
    if t >= beats[-1]:
        last = beats[-1] - beats[-2]
        return (len(beats) - 1) + (t - beats[-1]) / last
    i = bisect_right(beats, t) - 1
    return i + (t - beats[i]) / (beats[i + 1] - beats[i])


def _nearest_index(t: float, beats: Sequence[float]) -> int:
    """Index of the beat time closest to ``t``."""
    return min(range(len(beats)), key=lambda i: abs(beats[i] - t))


def _grid_error(fracs: Sequence[float], n: int) -> float:
    """Total snap error (in beat fractions) of onsets on an ``n``-grid."""
    return sum(abs(f - round(f * n) / n) for f in fracs)


def _infer_beats_per_measure(
    beats: Sequence[float], downbeat_times: Sequence[float]
) -> int:
    """Beats per measure from downbeat spacing; falls back to 4."""
    indices = sorted(_nearest_index(t, beats) for t in downbeat_times)
    diffs = [b - a for a, b in zip(indices, indices[1:]) if b > a]
    if not diffs:
        return 4
    return max(1, round(median(diffs)))


def quantize_notes(
    notes: Sequence[Note],
    beat_times: Sequence[float],
    downbeat_times: Sequence[float],
    subdivisions_per_beat: int = 4,
    triplet_subdivisions: int = 3,
    beats_per_measure: int | None = None,
    detect_triplets: bool = True,
) -> list[QuantizedNote]:
    """Snap ``notes`` onto the subdivision grid defined by ``beat_times``.

    ``beats_per_measure`` overrides the value inferred from downbeat spacing
    (constant time signature is assumed in this phase). Returns the notes
    sorted by quantized position, then pitch.
    """
    if subdivisions_per_beat < 1:
        raise ValueError("subdivisions_per_beat must be >= 1")
    if len(beat_times) < 2:
        raise ValueError("need at least two beat times to build a grid")
    beats = sorted(beat_times)
    if not notes:
        return []

    if beats_per_measure is None:
        beats_per_measure = _infer_beats_per_measure(beats, downbeat_times)
    # Beat index of the first downbeat: measure 1, beat 1 anchors there.
    first_db_idx = _nearest_index(downbeat_times[0], beats) if downbeat_times else 0

    # Group onsets by containing beat interval to pick each beat's grid.
    positions = [_beat_position(n.start_s, beats) for n in notes]
    fracs_by_beat: dict[int, list[float]] = {}
    for pos in positions:
        g = math.floor(pos + _EPS)
        fracs_by_beat.setdefault(g, []).append(pos - g)

    grid: dict[int, int] = {}
    for g, fracs in fracs_by_beat.items():
        n = subdivisions_per_beat
        if detect_triplets and triplet_subdivisions != subdivisions_per_beat:
            straight_err = _grid_error(fracs, subdivisions_per_beat)
            triplet_err = _grid_error(fracs, triplet_subdivisions)
            if triplet_err < straight_err:
                n = triplet_subdivisions
        grid[g] = n

    def n_of(g: int) -> int:
        return grid.get(g, subdivisions_per_beat)

    out: list[QuantizedNote] = []
    for note, pos in zip(notes, positions):
        g = math.floor(pos + _EPS)
        n = n_of(g)
        snapped = g + round((pos - g) * n) / n
        # An onset rounded up to the next beat line carries over (subdivision
        # 0 is shared by every grid, so the next beat's resolution applies).
        gf = math.floor(snapped + _EPS)
        n = n_of(gf)
        subdivision = round((snapped - gf) * n)

        end_pos = _beat_position(note.end_s, beats)
        snapped_end = round(end_pos * n) / n
        duration = max(1, round((snapped_end - snapped) * n))

        rel = gf - first_db_idx
        out.append(
            QuantizedNote(
                pitch_midi=note.pitch_midi,
                measure=1 + rel // beats_per_measure,
                beat=rel % beats_per_measure + 1,
                subdivision=subdivision,
                subdivisions_in_beat=n,
                duration_subdivisions=duration,
                start_s=note.start_s,
                end_s=note.end_s,
                velocity=note.velocity,
                confidence=note.confidence,
            )
        )
    out.sort(key=lambda q: (q.measure, q.beat, q.subdivision, q.pitch_midi))
    return out
