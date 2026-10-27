"""Hammer-on / pull-off detection from weak onsets (post-fretting heuristic).

A note is sounded by legato (hammer-on or pull-off) instead of a new pick
attack when ALL of these hold for it (the "target") and the previous note on
the SAME string (the "origin"):

- **Same string**: the origin is the latest note on the target's string that
  starts before the target. Notes on other strings in between do not matter.
- **Contiguous**: ``gap = target.start_s - origin.end_s`` satisfies
  ``-max_overlap_s <= gap <= max_gap_s``. A gap above ``max_gap_s`` is a
  *rest* on that string: the target follows silence and is therefore
  re-attacked, never legato. This is what keeps the first note of a measure
  after a rest from being marked (no measure logic is needed: the rest is
  the gap itself).
- **Weak attack**: ``target_velocity <= max_amplitude_ratio * origin_velocity``
  using ``Note.velocity`` (Basic Pitch's amplitude proxy). A target as loud
  as its origin was picked.
- **Fret interval**: ``1 <= |target.fret - origin.fret| <= max_fret_interval``
  (same fret = repeated note, too far = not reachable by a finger stretch).

Direction is decided by fret: a higher target fret is a hammer-on, a lower
one a pull-off (equivalent to pitch up/down on the same string). The
technique is written on the ORIGIN note with ``target_fret`` set to the
target's fret (see :class:`tabgen.core.models.Technique`). An origin that
already carries a technique is never overwritten.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from tabgen.core.models import (
    TECHNIQUE_HAMMER_ON,
    TECHNIQUE_PULL_OFF,
    Note,
    TabNote,
    Technique,
)


@dataclass(frozen=True)
class LegatoConfig:
    """Named thresholds of the legato heuristic (see module docstring)."""

    # Target velocity must be at most this fraction of the origin's.
    max_amplitude_ratio: float = 0.6
    # Largest silence (s) between origin end and target start (~3 frames of
    # Basic Pitch at 86 fps).
    max_gap_s: float = 0.035
    # Largest overlap (s) tolerated when the transcriber lets the origin
    # ring slightly past the target's onset.
    max_overlap_s: float = 0.05
    # Largest fret distance between origin and target.
    max_fret_interval: int = 5


def detect_legato(
    events: Sequence[TabNote],
    notes: Sequence[Note],
    config: LegatoConfig | None = None,
) -> list[TabNote]:
    """Return copies of ``events`` with hammer-on/pull-off techniques filled.

    ``notes`` is parallel to ``events``: ``notes[i]`` is the transcribed note
    that ``events[i]`` was fretted from (its ``velocity`` is the amplitude
    used for the weak-attack test). Inputs are never mutated; the returned
    list keeps the order of ``events``. Raises ``ValueError`` when the two
    sequences differ in length.
    """
    if len(events) != len(notes):
        raise ValueError(
            f"events and notes must be parallel; got {len(events)} events "
            f"and {len(notes)} notes"
        )
    cfg = config or LegatoConfig()
    result = list(events)

    order = sorted(
        range(len(events)), key=lambda i: (events[i].start_s, events[i].string)
    )
    last_on_string: dict[int, int] = {}
    for idx in order:
        target = events[idx]
        origin_idx = last_on_string.get(target.string)
        last_on_string[target.string] = idx
        if origin_idx is None:
            continue
        origin = result[origin_idx]
        if origin.technique is not None or origin.start_s >= target.start_s:
            continue
        gap = target.start_s - origin.end_s
        if gap > cfg.max_gap_s or gap < -cfg.max_overlap_s:
            continue
        origin_velocity = notes[origin_idx].velocity
        if origin_velocity <= 0:
            continue
        if notes[idx].velocity > cfg.max_amplitude_ratio * origin_velocity:
            continue
        interval = target.fret - origin.fret
        if interval == 0 or abs(interval) > cfg.max_fret_interval:
            continue
        kind = TECHNIQUE_HAMMER_ON if interval > 0 else TECHNIQUE_PULL_OFF
        result[origin_idx] = replace(
            origin, technique=Technique(kind=kind, target_fret=target.fret)
        )
    return result
