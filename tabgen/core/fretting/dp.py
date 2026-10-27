"""Assign (string, fret) to note events via dynamic programming (Viterbi).

Notes are grouped into *frames* of simultaneous onsets. For each frame every
feasible placement (one distinct string per note) is enumerated and scored
with an intra-frame cost (finger stretch, open strings out of context, high
frets, bonus for matching the active chord shape). A Viterbi pass over the
frame sequence then minimizes the total cost, where the transition cost is
the hand displacement between hand positions. A hand position is a window of
``position_span`` frets (index finger at the position, pinky at
``position + span - 1``); a fretted note inside the current window costs no
movement, and all-open frames keep the previous hand position.

String numbering in the result follows the guitarist convention: string 1 is
the **highest**-pitched string and string ``N`` the lowest (for standard
guitar, string 6 = low E). Internally strings are indexed low-to-high like
``tuning_midi``; ``string = n_strings - low_to_high_index``.

Out-of-range pitches are reported in ``FrettingResult.unassigned`` with a
reason; they are never silently dropped and never raise.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from tabgen.core.models import (
    BASS_STANDARD_TUNING,
    GUITAR_STANDARD_TUNING,
    ChordSegment,
    Note,
    NoteEvents,
)

# Canonical open/barre shapes for common chords, as the fret played on each
# string low-to-high (-1 = string not played). Defined for standard 6-string
# tuning; fret numbers are relative to the capo, so they remain valid with a
# capo. Unknown labels simply get no bonus.
CHORD_SHAPES: dict[str, list[int]] = {
    "C:maj": [-1, 3, 2, 0, 1, 0],
    "A:maj": [-1, 0, 2, 2, 2, 0],
    "A:min": [-1, 0, 2, 2, 1, 0],
    "G:maj": [3, 2, 0, 0, 0, 3],
    "E:maj": [0, 2, 2, 1, 0, 0],
    "E:min": [0, 2, 2, 0, 0, 0],
    "D:maj": [-1, -1, 0, 2, 3, 2],
    "D:min": [-1, -1, 0, 2, 3, 1],
    "F:maj": [1, 3, 3, 2, 1, 1],
    "B:min": [-1, 2, 4, 4, 3, 2],
}


@dataclass
class FrettingConfig:
    """Tuning, physical limits and cost weights for the fretting DP.

    All weights are named parameters so Phase 4 can tune them without code
    changes. Costs are in abstract "effort" units; lower is better.
    """

    # Open-string MIDI pitches, low-to-high (index 0 = lowest string).
    tuning_midi: list[int] = field(
        default_factory=lambda: list(GUITAR_STANDARD_TUNING)
    )
    capo_fret: int = 0
    max_fret: int = 24
    # Cost per fret of hand movement between consecutive frames.
    displacement_weight: float = 1.0
    # Cost per fret of span between the lowest and highest fretted note of
    # a frame (finger stretch inside a chord).
    stretch_weight: float = 0.7
    # Cost per open-string note not endorsed by the active chord shape
    # ("out of context" open string).
    open_string_penalty: float = 2.0
    # Bonus (subtracted) per note that matches the active chord shape.
    chord_shape_bonus: float = 3.0
    # Mild cost per fret number, pulling lines toward the nut when all
    # else is equal.
    high_fret_weight: float = 0.05
    # Mild cost per string index above the lowest string, per note. The
    # preference for lower (thicker) strings keeps melodic runs in the
    # conventional root-position box (e.g. A minor pentatonic at the 5th
    # fret) instead of drifting to equivalent shapes on higher strings
    # near the nut.
    string_index_weight: float = 0.4
    # Frets the hand covers without moving (one finger per fret: index at
    # the position, pinky at position + span - 1).
    position_span: int = 4
    # Notes whose onsets differ by less than this are one chord frame.
    simultaneity_epsilon_s: float = 0.03
    # Max placements kept per frame for the Viterbi pass.
    beam_width: int = 24


def guitar_config(**overrides) -> FrettingConfig:
    """Preset for a standard-tuned 6-string guitar."""
    return FrettingConfig(tuning_midi=list(GUITAR_STANDARD_TUNING), **overrides)


def bass_config(**overrides) -> FrettingConfig:
    """Preset for a standard-tuned 4-string bass."""
    return FrettingConfig(tuning_midi=list(BASS_STANDARD_TUNING), **overrides)


@dataclass
class FrettedNote:
    """A note placed on the fretboard.

    ``string`` is 1-based with string 1 = highest-pitched string (guitarist
    convention). ``fret`` is relative to the capo (0 = open string).
    """

    note: Note
    string: int
    fret: int


@dataclass
class UnassignedNote:
    """A note that could not be placed, with the reason why."""

    note: Note
    reason: str


@dataclass
class FrettingResult:
    """Output of :func:`assign_frets`."""

    assignments: list[FrettedNote] = field(default_factory=list)
    unassigned: list[UnassignedNote] = field(default_factory=list)


# A placement maps each note of a frame to (string_low_to_high_index, fret).
_Placement = tuple[tuple[int, int], ...]


def _candidates(pitch: int, config: FrettingConfig) -> list[tuple[int, int]]:
    """All (string_index, fret) that can sound ``pitch``, low string first."""
    found = []
    for s_idx, open_pitch in enumerate(config.tuning_midi):
        fret = pitch - (open_pitch + config.capo_fret)
        if 0 <= fret <= config.max_fret:
            found.append((s_idx, fret))
    return found


def _group_frames(notes: list[Note], epsilon_s: float) -> list[list[Note]]:
    """Group notes whose onsets coincide within ``epsilon_s`` seconds."""
    frames: list[list[Note]] = []
    for note in sorted(notes, key=lambda n: (n.start_s, n.pitch_midi)):
        if frames and note.start_s - frames[-1][0].start_s <= epsilon_s:
            frames[-1].append(note)
        else:
            frames.append([note])
    return frames


def _active_chord(
    chords: list[ChordSegment] | None, time_s: float
) -> str | None:
    """Harte label of the chord sounding at ``time_s`` (None if none)."""
    if not chords:
        return None
    for segment in chords:
        if segment.start_s <= time_s < segment.end_s and segment.label != "N":
            # Strip inversions, e.g. "C:maj/3" -> "C:maj".
            return segment.label.split("/")[0]
    return None


def _chord_shape(
    label: str | None, config: FrettingConfig
) -> list[int] | None:
    """Shape frets for ``label`` when applicable to the configured tuning."""
    if label is None or config.tuning_midi != GUITAR_STANDARD_TUNING:
        return None
    return CHORD_SHAPES.get(label)


def _enumerate_placements(
    frame: list[Note],
    candidates: list[list[tuple[int, int]]],
    n_strings: int,
) -> list[_Placement]:
    """All complete placements of the frame on pairwise-distinct strings."""
    if len(frame) > n_strings:
        return []
    placements: list[_Placement] = []
    for combo in itertools.product(*candidates):
        strings = [s for s, _ in combo]
        if len(set(strings)) == len(strings):
            placements.append(combo)
    return placements


def _greedy_placement(
    frame: list[Note],
    candidates: list[list[tuple[int, int]]],
) -> tuple[list[tuple[int, tuple[int, int]]], list[int]]:
    """Fallback: place notes one by one (fewest candidates first).

    Returns (placed, leftover_indices): ``placed`` holds
    (note_index, (string, fret)) pairs; ``leftover_indices`` are notes that
    found no free string.
    """
    order = sorted(range(len(frame)), key=lambda i: len(candidates[i]))
    used: set[int] = set()
    placed: list[tuple[int, tuple[int, int]]] = []
    leftover: list[int] = []
    for i in order:
        free = [(s, f) for s, f in candidates[i] if s not in used]
        if not free:
            leftover.append(i)
            continue
        choice = min(free, key=lambda sf: sf[1])
        used.add(choice[0])
        placed.append((i, choice))
    placed.sort(key=lambda item: item[0])
    return placed, leftover


def _frame_cost(
    placement: _Placement,
    shape: list[int] | None,
    config: FrettingConfig,
) -> float:
    """Intra-frame cost: stretch, open strings, high frets, chord bonus."""
    cost = 0.0
    fretted = [fret for _, fret in placement if fret > 0]
    if len(fretted) >= 2:
        cost += config.stretch_weight * (max(fretted) - min(fretted))
    for s_idx, fret in placement:
        endorsed = shape is not None and shape[s_idx] == fret
        if fret == 0 and not endorsed:
            cost += config.open_string_penalty
        if endorsed:
            cost -= config.chord_shape_bonus
        cost += config.high_fret_weight * fret
        cost += config.string_index_weight * s_idx
    return cost


def _positions(placement: _Placement, span: int) -> list[int | None]:
    """Hand positions from which ``placement`` is playable.

    ``None`` means "any position" (all strings open: the hand does not
    move). When the placement spans more than ``span`` frets, the lowest
    fretted fret is used as the single anchor position.
    """
    fretted = [fret for _, fret in placement if fret > 0]
    if not fretted:
        return [None]
    low, high = min(fretted), max(fretted)
    first = max(0, high - span + 1)
    if first > low:  # wider than the hand: anchor at the lowest fret
        return [low]
    return list(range(first, low + 1))


def assign_frets(
    notes: NoteEvents | list[Note],
    config: FrettingConfig | None = None,
    chords: list[ChordSegment] | None = None,
) -> FrettingResult:
    """Assign a (string, fret) to each note by Viterbi over chord frames.

    ``chords`` is the optional ``AnalysisResult.chords`` list from stage 2;
    when the active chord has a known shape (see :data:`CHORD_SHAPES`),
    matching placements get a bonus. Out-of-range notes are returned in
    ``FrettingResult.unassigned`` instead of being dropped or raising.
    """
    if config is None:
        config = guitar_config()
    note_list = notes.notes if isinstance(notes, NoteEvents) else list(notes)
    n_strings = len(config.tuning_midi)
    result = FrettingResult()

    # Build frames; peel off out-of-range notes before placement.
    frames: list[list[Note]] = []
    frame_candidates: list[list[list[tuple[int, int]]]] = []
    for frame in _group_frames(note_list, config.simultaneity_epsilon_s):
        playable: list[Note] = []
        cands: list[list[tuple[int, int]]] = []
        for note in frame:
            found = _candidates(note.pitch_midi, config)
            if found:
                playable.append(note)
                cands.append(found)
            else:
                result.unassigned.append(
                    UnassignedNote(
                        note=note,
                        reason=(
                            f"pitch {note.pitch_midi} not playable with "
                            f"tuning {config.tuning_midi}, capo "
                            f"{config.capo_fret}, max fret {config.max_fret}"
                        ),
                    )
                )
        if playable:
            frames.append(playable)
            frame_candidates.append(cands)

    if not frames:
        return result

    # Per frame: enumerate placements, score them, keep the best beam.
    kept_frames: list[list[Note]] = []
    frame_states: list[list[tuple[_Placement, float]]] = []
    for frame, cands in zip(frames, frame_candidates):
        shape = _chord_shape(_active_chord(chords, frame[0].start_s), config)
        placements = _enumerate_placements(frame, cands, n_strings)
        if not placements:
            placed, leftover = _greedy_placement(frame, cands)
            for i in leftover:
                result.unassigned.append(
                    UnassignedNote(
                        note=frame[i],
                        reason="no free string in simultaneous-note frame",
                    )
                )
            if not placed:
                continue
            frame = [frame[i] for i, _ in placed]
            placements = [tuple(sf for _, sf in placed)]
        scored = [(p, _frame_cost(p, shape, config)) for p in placements]
        scored.sort(key=lambda item: item[1])
        kept_frames.append(frame)
        frame_states.append(scored[: config.beam_width])
    frames = kept_frames

    if not frame_states:
        return result

    # Expand placements into (placement, hand_position) Viterbi states. An
    # all-open frame (position None) inherits the predecessor's position.
    states: list[list[tuple[int, int | None, float]]] = []
    for scored in frame_states:
        expanded: list[tuple[int, int | None, float]] = []
        for idx, (placement, emission) in enumerate(scored):
            for pos in _positions(placement, config.position_span):
                expanded.append((idx, pos, emission))
        states.append(expanded)

    # back[t][k] = (total_cost, predecessor_state, effective_position).
    back: list[list[tuple[float, int, int | None]]] = [
        [(emission, -1, pos) for _, pos, emission in states[0]]
    ]
    for t in range(1, len(states)):
        row: list[tuple[float, int, int | None]] = []
        for _, pos, emission in states[t]:
            best: tuple[float, int, int | None] = (float("inf"), -1, pos)
            for j, (prev_cost, _, prev_pos) in enumerate(back[t - 1]):
                eff = pos if pos is not None else prev_pos
                move = 0.0
                if eff is not None and prev_pos is not None:
                    move = config.displacement_weight * abs(eff - prev_pos)
                total = prev_cost + move + emission
                if total < best[0]:
                    best = (total, j, eff)
            row.append(best)
        back.append(row)

    # Backtrack the cheapest path and emit assignments in time order.
    path: list[int] = []
    k = min(range(len(back[-1])), key=lambda i: back[-1][i][0])
    for t in range(len(back) - 1, -1, -1):
        path.append(k)
        k = back[t][k][1]
    path.reverse()

    for t, k in enumerate(path):
        placement = frame_states[t][states[t][k][0]][0]
        for note, (s_idx, fret) in zip(frames[t], placement):
            result.assignments.append(
                FrettedNote(note=note, string=n_strings - s_idx, fret=fret)
            )
    return result
