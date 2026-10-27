"""Detect bends and slides from Basic Pitch's per-note pitch-bend curves.

Input is a fretted score (``TabNote`` events) plus the source ``Note`` of
each event, whose ``bends`` list holds one pitch offset per model frame in
1/3-semitone bins relative to ``pitch_midi``.

- **Bend**: the smoothed curve stays at least ``min_bend_semitones`` above
  the fretted pitch for at least ``min_bend_duration_s``. Short vibrato and
  frame-level pitch noise are removed by the median smoothing and the
  duration gate. The peak is reported in half-semitone steps; the curve
  shape (rise, hold, optional release) goes to ``Technique.bend_curve``.
- **Slide**: two consecutive notes on the same string, adjacent in time,
  with a pitch glide between them (the tail of the first note moves
  towards the second, or the head of the second arrives from the first).
  The technique sits on the first note; ``target_fret`` is the second
  note's fret.

Slides are decided before bends: a glide that ends on the next note is a
slide, not a bend. Existing techniques are never overwritten.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

from tabgen.core.models import (
    SLIDE_DOWN,
    SLIDE_UP,
    TECHNIQUE_BEND,
    TECHNIQUE_SLIDE,
    Note,
    TabNote,
    Technique,
)

# Basic Pitch frame rate: ANNOTATIONS_FPS = AUDIO_SAMPLE_RATE // FFT_HOP
# = 22050 // 256 = 86 frames per second (basic_pitch/constants.py).
BASIC_PITCH_FPS = 86
# Basic Pitch contour resolution: CONTOURS_BINS_PER_SEMITONE = 3.
BASIC_PITCH_BINS_PER_SEMITONE = 3


@dataclass(frozen=True)
class BendConfig:
    """Named thresholds of the bend/slide detector.

    - ``smoothing_frames``: odd median-filter window over the bend curve
      (5 frames ~ 58 ms at 86 fps) that removes isolated noisy frames.
    - ``min_bend_semitones``: minimum smoothed deviation above the fretted
      pitch that counts as bent. 0.75 sits between the 2/3-semitone bin
      (two bins, still pitch noise/vibrato) and a half-step (three bins).
    - ``min_bend_duration_s``: minimum time the curve must stay above
      ``min_bend_semitones`` (sustained deviation, not a blip).
    - ``bend_step_semitones``: rounding step of ``bend_semitones`` and of
      the curve points (0.5 = quarter-tone, the Guitar Pro resolution).
    - ``curve_points``: number of evenly spaced samples in ``bend_curve``.
    - ``slide_max_gap_s``: largest silence between the two notes of a slide.
    - ``slide_window_s``: span at the end of the first note / start of the
      second note scanned for the glide.
    - ``min_slide_glide_semitones``: minimum glide towards the other note
      seen in that window.
    - ``fps``: frame rate of ``Note.bends``.
    """

    smoothing_frames: int = 5
    min_bend_semitones: float = 0.75
    min_bend_duration_s: float = 0.05
    bend_step_semitones: float = 0.5
    curve_points: int = 5
    slide_max_gap_s: float = 0.05
    slide_window_s: float = 0.1
    min_slide_glide_semitones: float = 1.0
    fps: float = BASIC_PITCH_FPS


def detect_bends_and_slides(
    events: Sequence[TabNote],
    notes: Sequence[Note],
    config: BendConfig | None = None,
) -> list[TabNote]:
    """Return copies of events with technique filled.

    An existing technique is never overwritten. ``notes[i]`` must be the
    source note of ``events[i]`` (its ``bends`` feed the detector). Inputs
    are not mutated.
    """
    if len(events) != len(notes):
        raise ValueError(
            f"events and notes must be parallel: {len(events)} != {len(notes)}"
        )
    cfg = config or BendConfig()
    curves = [_semitone_curve(n.bends, cfg) for n in notes]
    techniques: list[Technique | None] = [e.technique for e in events]

    for first, second in _same_string_pairs(events):
        if techniques[first] is not None:
            continue
        slide = _slide(
            events[first], events[second], curves[first], curves[second], cfg
        )
        if slide is not None:
            techniques[first] = slide

    for i, curve in enumerate(curves):
        if techniques[i] is None:
            techniques[i] = _bend(curve, cfg)

    return [replace(event, technique=tech) for event, tech in zip(events, techniques)]


def _semitone_curve(bends: list[int] | None, cfg: BendConfig) -> list[float]:
    """Median-smoothed bend curve in semitones (empty when no data)."""
    if not bends:
        return []
    offsets = [b / BASIC_PITCH_BINS_PER_SEMITONE for b in bends]
    return _median_filter(offsets, cfg.smoothing_frames)


def _median_filter(values: list[float], window: int) -> list[float]:
    """Centered running median; the window shrinks at the edges."""
    if window <= 1:
        return list(values)
    half = window // 2
    out: list[float] = []
    for i in range(len(values)):
        chunk = sorted(values[max(0, i - half) : i + half + 1])
        mid = len(chunk) // 2
        out.append(chunk[mid] if len(chunk) % 2 else (chunk[mid - 1] + chunk[mid]) / 2)
    return out


def _round_step(value: float, step: float) -> float:
    return round(value / step) * step if step > 0 else value


def _bend(curve: list[float], cfg: BendConfig) -> Technique | None:
    """Bend technique when the curve holds above the threshold long enough."""
    if not curve:
        return None
    min_frames = max(1, math.ceil(cfg.min_bend_duration_s * cfg.fps))
    best_start, best_len, run_start = -1, 0, -1
    for i, value in enumerate([*curve, -math.inf]):
        if value >= cfg.min_bend_semitones:
            if run_start < 0:
                run_start = i
        elif run_start >= 0:
            if i - run_start > best_len:
                best_start, best_len = run_start, i - run_start
            run_start = -1
    if best_len < min_frames:
        return None
    peak = max(curve[best_start : best_start + best_len])
    semitones = _round_step(peak, cfg.bend_step_semitones)
    if semitones <= 0:
        return None
    return Technique(
        kind=TECHNIQUE_BEND,
        bend_semitones=semitones,
        bend_curve=_sample_curve(curve, cfg),
    )


def _sample_curve(curve: list[float], cfg: BendConfig) -> list[float]:
    """``cfg.curve_points`` evenly spaced, non-negative, rounded samples."""
    count = max(2, cfg.curve_points)
    last = len(curve) - 1
    points = []
    for k in range(count):
        value = curve[round(k * last / (count - 1))]
        points.append(max(0.0, _round_step(value, cfg.bend_step_semitones)))
    return points


def _same_string_pairs(events: Sequence[TabNote]) -> list[tuple[int, int]]:
    """Index pairs of consecutive events (by ``start_s``) on each string."""
    by_string: dict[int, list[int]] = {}
    for i, event in enumerate(events):
        by_string.setdefault(event.string, []).append(i)
    pairs: list[tuple[int, int]] = []
    for indices in by_string.values():
        ordered = sorted(indices, key=lambda i: (events[i].start_s, i))
        pairs.extend(zip(ordered, ordered[1:]))
    return pairs


def _slide(
    first: TabNote,
    second: TabNote,
    first_curve: list[float],
    second_curve: list[float],
    cfg: BendConfig,
) -> Technique | None:
    """Slide from ``first`` into ``second`` when a pitch glide links them."""
    if first.fret == second.fret:
        return None
    if second.start_s - first.end_s > cfg.slide_max_gap_s:
        return None
    direction = 1 if second.fret > first.fret else -1
    window = max(1, round(cfg.slide_window_s * cfg.fps))
    # Tail of the first note rising (or falling) towards the second note.
    tail = [direction * v for v in first_curve[-window:]]
    # Head of the second note arriving from the first note's side.
    head = [-direction * v for v in second_curve[:window]]
    glide = max([0.0, *tail, *head])
    if glide < cfg.min_slide_glide_semitones:
        return None
    return Technique(
        kind=TECHNIQUE_SLIDE,
        slide_direction=SLIDE_UP if direction > 0 else SLIDE_DOWN,
        target_fret=second.fret,
    )
