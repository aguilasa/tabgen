"""Export TabScore(s) to a Guitar Pro 5 (.gp5) file via PyGuitarPro.

One track is written per :class:`~tabgen.core.models.TabScore` (e.g. guitar
and bass), carrying its tuning (any string count, e.g. a 5-string bass),
capo (GP5 track ``offset``), General MIDI program (from ``instrument`` and
``instrument_type`` via :func:`~tabgen.core.models.gm_program`), BPM, key
signature and time signature. Notes are placed at string/fret with durations
quantized on the score grid; gaps are filled with rests so every measure sums
exactly to the time signature. Chord labels are annotated on the first beat
of their measure.

Conventions (mirroring the fretting stage and PyGuitarPro itself):

- Guitarist string numbering: string 1 is the highest-pitched string, string
  N the lowest; the open pitch of string ``s`` is ``tuning_midi[N - s]`` and
  the sounding pitch adds ``fret`` plus ``capo_fret``.
- ``TabNote`` carries no grid resolution, so the caller passes
  ``beat_grids``: per score, a list parallel to ``events`` with each note's
  subdivisions-per-beat (4 straight / 3 triplet), exactly
  ``QuantizedNote.subdivisions_in_beat``. It is JSON-trivial (list of lists
  of ints); omitted entries default to ``default_subdivisions_in_beat``.
- Overlapping notes on one track are truncated at the next onset (single
  tab voice); simultaneous onsets become one beat (a chord), lasting the
  shortest of their durations.
- A note whose duration crosses a measure boundary (or that has no single
  Guitar Pro duration) is split into tied beats (``NoteType.tie``).
- ``TabNote.technique`` maps to the Guitar Pro note effects of the origin
  note: a bend becomes a ``BendEffect`` (``BendType.bend``) on the note's
  first beat, with ``bend_curve`` as evenly spaced points over positions
  0..12 (values in quarter tones, PyGuitarPro's unit) or, without a curve,
  a rise to ``bend_semitones`` that holds; a slide becomes
  ``SlideType.shiftSlideTo`` and a hammer-on or pull-off sets
  ``NoteEffect.hammer`` (GP5 uses one flag for both; the direction follows
  from the next fret), both on the note's last beat so they link into the
  next note on the string.

This module is pure core: no print/typer/rich.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import guitarpro as gp

from tabgen.core.models import (
    TECHNIQUE_BEND,
    TECHNIQUE_HAMMER_ON,
    TECHNIQUE_PULL_OFF,
    TECHNIQUE_SLIDE,
    TabScore,
    Technique,
    gm_program,
)

# Ticks of a whole note on the Guitar Pro grid (quarter = 960).
_WHOLE_TICKS = gp.Duration.quarterTime * 4

# Chord label meaning "no chord" in Harte notation; never annotated.
_NO_CHORD = "N"


class Gp5ExportError(RuntimeError):
    """Raised when TabScores cannot be written as a .gp5 file."""


def _duration_atoms() -> list[tuple[int, int, bool, bool]]:
    """Writable Guitar Pro durations as (ticks, value, dotted, triplet).

    Sorted by ticks, descending, so a greedy decomposition can split any
    grid-aligned gap or note length into representable chunks.
    """
    atoms: list[tuple[int, int, bool, bool]] = []
    for value in (1, 2, 4, 8, 16, 32, 64, 128):
        base = _WHOLE_TICKS // value
        atoms.append((base * 3 // 2, value, True, False))
        atoms.append((base, value, False, False))
        if base * 2 % 3 == 0:
            atoms.append((base * 2 // 3, value, False, True))
    atoms.sort(key=lambda a: a[0], reverse=True)
    return atoms


_ATOMS = _duration_atoms()


def _split_ticks(ticks: int) -> list[gp.Duration]:
    """Decompose ``ticks`` into a list of Guitar Pro durations (greedy)."""
    out: list[gp.Duration] = []
    remaining = ticks
    while remaining > 0:
        for atom_ticks, value, dotted, triplet in _ATOMS:
            if atom_ticks <= remaining:
                tuplet = gp.Tuplet(3, 2) if triplet else gp.Tuplet(1, 1)
                out.append(gp.Duration(value, isDotted=dotted, tuplet=tuplet))
                remaining -= atom_ticks
                break
        else:
            raise Gp5ExportError(
                f"cannot represent {ticks} ticks as Guitar Pro durations"
            )
    return out


def _key_signature(key: str) -> gp.KeySignature:
    """Map a '<tonic> <mode>' key (e.g. 'A minor') to a GP key signature.

    Unknown or enharmonically unsupported keys fall back to C major.
    """
    parts = key.strip().split()
    if len(parts) != 2 or not parts[0]:
        return gp.KeySignature.CMajor
    tonic, mode = parts
    letter = tonic[0].upper()
    suffix = {"": "", "#": "Sharp", "b": "Flat"}.get(tonic[1:])
    mode_name = mode.capitalize()
    if suffix is None or mode_name not in ("Major", "Minor"):
        return gp.KeySignature.CMajor
    name = f"{letter}{mode_name}{suffix}"
    return getattr(gp.KeySignature, name, gp.KeySignature.CMajor)


@dataclass
class _Segment:
    """A beat-to-be: simultaneous notes over one in-measure tick span."""

    start: int  # absolute ticks from measure 1, beat 1
    duration: int  # ticks, never crossing a measure boundary
    notes: list[tuple[int, int, Technique | None]]  # (string, fret, technique)
    tied: bool  # continuation of a note split at a boundary
    last: bool = True  # final chunk of its note (link effects go here)


@dataclass
class _TrackPlan:
    """One TabScore resolved to tick segments grouped by measure."""

    score: TabScore
    segments_by_measure: dict[int, list[_Segment]] = field(default_factory=dict)
    chords_by_measure: dict[int, str] = field(default_factory=dict)
    last_measure: int = 1


def _grid_ticks(units: int, beat_ticks: int, grid: int, what: str) -> int:
    """Convert ``units`` subdivisions of a ``grid``-per-beat into ticks."""
    total = units * beat_ticks
    if grid < 1 or total % grid:
        raise Gp5ExportError(
            f"{what}: {units} subdivisions of a {grid}-grid do not align "
            f"with the {beat_ticks}-tick beat"
        )
    return total // grid


def _plan_track(
    score: TabScore,
    grids: Sequence[int],
    beat_ticks: int,
    measure_ticks: int,
    measure_offset: int,
) -> _TrackPlan:
    """Resolve a score's events into non-overlapping measure segments."""
    n_strings = len(score.tuning_midi)
    # start, duration, string, fret, technique
    onsets: list[tuple[int, int, int, int, Technique | None]] = []
    for index, (event, grid) in enumerate(zip(score.events, grids)):
        what = f"{score.instrument} event {index}"
        if not 1 <= event.string <= n_strings:
            raise Gp5ExportError(
                f"{what}: string {event.string} outside 1..{n_strings}"
            )
        if event.fret < 0:
            raise Gp5ExportError(f"{what}: negative fret {event.fret}")
        if event.duration_subdivisions < 1:
            raise Gp5ExportError(f"{what}: duration must be >= 1 subdivision")
        start = (
            (event.measure - 1 + measure_offset) * measure_ticks
            + (event.beat - 1) * beat_ticks
            + _grid_ticks(event.subdivision, beat_ticks, grid, what)
        )
        duration = _grid_ticks(
            event.duration_subdivisions, beat_ticks, grid, what
        )
        onsets.append((start, duration, event.string, event.fret, event.technique))
    onsets.sort(key=lambda o: (o[0], o[2]))

    # Simultaneous onsets form one beat; it lasts their shortest duration.
    grouped: list[_Segment] = []
    for start, duration, string, fret, technique in onsets:
        if grouped and grouped[-1].start == start:
            grouped[-1].notes.append((string, fret, technique))
            grouped[-1].duration = min(grouped[-1].duration, duration)
        else:
            grouped.append(
                _Segment(start, duration, [(string, fret, technique)], False)
            )

    plan = _TrackPlan(score=score)
    for current, nxt in zip(grouped, grouped[1:] + [None]):
        if nxt is not None:  # truncate at the next onset (single voice)
            current.duration = min(current.duration, nxt.start - current.start)
        # Split at measure boundaries; continuations are tied.
        start, remaining, tied = current.start, current.duration, False
        while remaining > 0:
            measure = start // measure_ticks + 1
            boundary = measure * measure_ticks
            chunk = min(remaining, boundary - start)
            plan.segments_by_measure.setdefault(measure, []).append(
                _Segment(start, chunk, current.notes, tied, chunk == remaining)
            )
            plan.last_measure = max(plan.last_measure, measure)
            start, remaining, tied = start + chunk, remaining - chunk, True

    for chord in score.chords:
        if chord.label and chord.label != _NO_CHORD:
            measure = chord.measure + measure_offset
            plan.chords_by_measure[measure] = chord.label
            plan.last_measure = max(plan.last_measure, measure)
    return plan


def _bend_effect(technique: Technique) -> gp.BendEffect:
    """Guitar Pro bend for a bend technique (point values in quarter tones)."""
    per_semitone = 2 * gp.BendEffect.semitoneLength  # PyGuitarPro: 1 = 1/4 tone
    max_position = gp.BendEffect.maxPosition
    curve = list(technique.bend_curve)
    if len(curve) >= 2:
        last = len(curve) - 1
        shape = [
            (round(k * max_position / last), value) for k, value in enumerate(curve)
        ]
    else:
        peak = technique.bend_semitones
        shape = [(0, 0.0), (max_position // 2, peak), (max_position, peak)]
    points = [
        gp.BendPoint(
            position=position,
            value=min(gp.BendEffect.maxValue, max(0, round(value * per_semitone))),
        )
        for position, value in shape
    ]
    # BendEffect.value: Guitar Pro's 1/100-tone amount (100 = whole step).
    return gp.BendEffect(
        type=gp.BendType.bend,
        value=round(technique.bend_semitones * 50),
        points=points,
    )


def _apply_technique(
    note: gp.Note, technique: Technique | None, first: bool, last: bool
) -> None:
    """Write ``technique`` as effects of ``note`` (see module docstring)."""
    if technique is None:
        return
    if technique.kind == TECHNIQUE_BEND and first:
        note.effect.bend = _bend_effect(technique)
    elif technique.kind == TECHNIQUE_SLIDE and last:
        note.effect.slides = [gp.SlideType.shiftSlideTo]
    elif technique.kind in (TECHNIQUE_HAMMER_ON, TECHNIQUE_PULL_OFF) and last:
        note.effect.hammer = True


def _append_beats(
    voice: gp.Voice,
    durations: Sequence[gp.Duration],
    notes: Sequence[tuple[int, int, Technique | None]],
    tied: bool,
    last: bool = True,
) -> None:
    """Append note beats (tie-chained) or rest beats to ``voice``.

    ``tied`` marks the first duration as a continuation of the note;
    ``last`` marks this chunk as the note's final one (link effects go on
    its final beat).
    """
    for index, duration in enumerate(durations):
        if notes:
            beat = gp.Beat(voice, duration=duration, status=gp.BeatStatus.normal)
            note_type = gp.NoteType.tie if tied else gp.NoteType.normal
            final = last and index == len(durations) - 1
            for string, fret, technique in notes:
                note = gp.Note(beat, value=fret, string=string, type=note_type)
                _apply_technique(note, technique, not tied, final)
                beat.notes.append(note)
            tied = True  # chunks after the first continue the same note
        else:
            beat = gp.Beat(voice, duration=duration, status=gp.BeatStatus.rest)
        voice.beats.append(beat)


def _fill_measure(
    measure: gp.Measure,
    segments: Sequence[_Segment],
    measure_ticks: int,
    chord_label: str | None,
    n_strings: int,
) -> None:
    """Write a measure's beats: notes in order, rests filling every gap."""
    voice = measure.voices[0]
    measure_start = (measure.header.number - 1) * measure_ticks
    cursor = measure_start
    for segment in segments:
        if segment.start > cursor:
            _append_beats(voice, _split_ticks(segment.start - cursor), [], False)
        _append_beats(
            voice,
            _split_ticks(segment.duration),
            segment.notes,
            segment.tied,
            segment.last,
        )
        cursor = segment.start + segment.duration
    if cursor < measure_start + measure_ticks:
        remaining = measure_start + measure_ticks - cursor
        _append_beats(voice, _split_ticks(remaining), [], False)
    if chord_label:
        chord = gp.Chord(length=n_strings, name=chord_label, firstFret=0)
        voice.beats[0].effect.chord = chord


def export_gp5(
    scores: TabScore | Sequence[TabScore],
    output_path: str | Path,
    beat_grids: Sequence[Sequence[int]] | None = None,
    default_subdivisions_in_beat: int = 4,
    title: str = "",
) -> Path:
    """Write one or more ``TabScore`` as a Guitar Pro 5 file.

    ``beat_grids`` runs parallel to ``scores``; each entry runs parallel to
    that score's ``events`` and gives the note's subdivisions-per-beat
    (``QuantizedNote.subdivisions_in_beat``: 4 straight, 3 triplet). When
    ``None`` (or for any missing entry) ``default_subdivisions_in_beat``
    applies. All scores must share the same time signature (tracks share
    measure headers). Returns the path of the written file.
    """
    score_list = [scores] if isinstance(scores, TabScore) else list(scores)
    if not score_list:
        raise Gp5ExportError("no TabScore to export")
    if beat_grids is not None and len(beat_grids) != len(score_list):
        raise Gp5ExportError(
            f"beat_grids length {len(beat_grids)} does not match "
            f"score count {len(score_list)}"
        )

    numerator, denominator = score_list[0].time_signature
    for score in score_list:
        if score.time_signature != [numerator, denominator]:
            raise Gp5ExportError(
                "all scores must share one time signature; got "
                f"{score.time_signature} vs {[numerator, denominator]}"
            )
    if numerator < 1 or denominator < 1 or _WHOLE_TICKS % denominator:
        raise Gp5ExportError(
            f"unsupported time signature {numerator}/{denominator}"
        )
    beat_ticks = _WHOLE_TICKS // denominator
    measure_ticks = numerator * beat_ticks

    # Anacrusis measures (<= 0) shift right so the score starts at measure 1.
    min_measure = min(
        (event.measure for score in score_list for event in score.events),
        default=1,
    )
    measure_offset = max(0, 1 - min_measure)

    plans: list[_TrackPlan] = []
    for index, score in enumerate(score_list):
        grids = list(beat_grids[index]) if beat_grids is not None else []
        if len(grids) < len(score.events):
            grids += [default_subdivisions_in_beat] * (
                len(score.events) - len(grids)
            )
        plans.append(
            _plan_track(score, grids, beat_ticks, measure_ticks, measure_offset)
        )
    total_measures = max(plan.last_measure for plan in plans)

    song = gp.Song()
    song.tracks.clear()
    song.measureHeaders.clear()
    song.title = title
    song.tempo = max(1, round(score_list[0].tempo_bpm))
    key_signature = _key_signature(score_list[0].key)
    song.key = key_signature

    for number in range(1, total_measures + 1):
        song.measureHeaders.append(
            gp.MeasureHeader(
                number=number,
                start=gp.Duration.quarterTime + (number - 1) * measure_ticks,
                timeSignature=gp.TimeSignature(numerator, gp.Duration(denominator)),
                keySignature=key_signature,
            )
        )

    for index, plan in enumerate(plans):
        score = plan.score
        n_strings = len(score.tuning_midi)
        track = gp.Track(
            song, number=index + 1, name=score.instrument, measures=[]
        )
        # String 1 is the highest-pitched: reverse the low-to-high tuning.
        track.strings = [
            gp.GuitarString(number=position + 1, value=pitch)
            for position, pitch in enumerate(reversed(score.tuning_midi))
        ]
        track.offset = score.capo_fret  # GP5 capo
        track.channel.instrument = gm_program(
            score.instrument, score.instrument_type
        )
        track.channel.channel = index * 2
        track.channel.effectChannel = index * 2 + 1
        for header in song.measureHeaders:
            measure = gp.Measure(track, header)
            _fill_measure(
                measure,
                plan.segments_by_measure.get(header.number, []),
                measure_ticks,
                plan.chords_by_measure.get(header.number),
                n_strings,
            )
            track.measures.append(measure)
        song.tracks.append(track)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gp.write(song, str(output_path))
    return output_path
