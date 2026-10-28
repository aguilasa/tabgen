"""Export TabScore(s) to a MusicXML file via music21.

One part is written per :class:`~tabgen.core.models.TabScore` (e.g. guitar
and bass), carrying its key signature, time signature, BPM (metronome mark on
the first part) and chord symbols. Notes carry the sounding pitch (open
string + fret + capo) plus string/fret technical indications, so readers get
both the staff and the tablature placement; a dedicated TAB staff is out of
scope (fine engraving).

Conventions (mirroring the gp5 exporter):

- Guitarist string numbering: string 1 is the highest-pitched string, string
  N the lowest; the open pitch of string ``s`` is ``tuning_midi[N - s]`` and
  the sounding pitch adds ``fret`` plus ``capo_fret``.
- ``beat_grids``: per score, a list parallel to ``events`` with each note's
  subdivisions-per-beat (4 straight / 3 triplet,
  ``QuantizedNote.subdivisions_in_beat``); omitted entries default to
  ``default_subdivisions_in_beat``. Triplets become proper music21 tuplet
  durations (quarterLength fractions such as 1/3).
- Overlapping notes in one part are truncated at the next onset (single tab
  voice); simultaneous onsets become one chord, lasting the shortest of
  their durations.
- A note whose duration crosses a measure boundary (or that has no single
  notatable duration) is split into tied notes; gaps are filled with rests
  so every measure sums exactly to the time signature.
- ``TabNote.technique`` maps to MusicXML notations: a bend becomes a
  ``<technical><bend>`` (music21 ``FretBend``, ``bend-alter`` =
  ``bend_semitones``) on the note's first element; a slide becomes a solid
  ``<slide>`` (music21 ``Glissando``, ``slideType="continuous"``) and a
  hammer-on / pull-off a ``<hammer-on>`` / ``<pull-off>`` start/stop pair
  (music21 ``HammerOn`` / ``PullOff`` spanners), each spanning from the
  origin note's last element to the next note on the same string. Link
  techniques with no later note on their string are dropped.
- Harte chord labels (e.g. ``A:min``) map to music21 chord symbols on the
  first beat of their measure; ``N`` (no chord) and unknown labels are
  skipped.

This module is pure core: no print/typer/rich.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Sequence

from music21 import articulations as m21articulations
from music21 import chord as m21chord
from music21 import harmony as m21harmony
from music21 import interval as m21interval
from music21 import key as m21key
from music21 import metadata as m21metadata
from music21 import meter as m21meter
from music21 import note as m21note
from music21 import pitch as m21pitch
from music21 import spanner as m21spanner
from music21 import stream as m21stream
from music21 import tempo as m21tempo
from music21 import tie as m21tie

from tabgen.core.models import (
    TECHNIQUE_BEND,
    TECHNIQUE_HAMMER_ON,
    TECHNIQUE_PULL_OFF,
    TECHNIQUE_SLIDE,
    TabScore,
    Technique,
)

# Internal tick grid, mirroring the gp5 exporter (quarter note = 960 ticks).
_QUARTER_TICKS = 960
_WHOLE_TICKS = _QUARTER_TICKS * 4

# Chord label meaning "no chord" in Harte notation; never annotated.
_NO_CHORD = "N"

# Harte chord qualities mapped to music21 chord-symbol figure suffixes.
_HARTE_TO_FIGURE: dict[str, str] = {
    "maj": "",
    "min": "m",
    "7": "7",
    "maj7": "maj7",
    "min7": "m7",
    "dim": "dim",
    "aug": "+",
    "sus4": "sus4",
    "sus2": "sus2",
}


class MusicXmlExportError(RuntimeError):
    """Raised when TabScores cannot be written as a MusicXML file."""


def _duration_atoms() -> list[tuple[int, Fraction]]:
    """Notatable durations as (ticks, quarterLength), ticks descending.

    Plain, dotted and triplet variants of whole..64th notes; a greedy
    decomposition splits any grid-aligned span into representable chunks
    (each quarterLength maps to a simple music21 duration, tuplets included).
    """
    atoms: list[tuple[int, Fraction]] = []
    for value in (1, 2, 4, 8, 16, 32, 64):
        base = _WHOLE_TICKS // value
        atoms.append((base * 3 // 2, Fraction(6, value)))  # dotted
        atoms.append((base, Fraction(4, value)))  # plain
        if base * 2 % 3 == 0:
            atoms.append((base * 2 // 3, Fraction(8, 3 * value)))  # triplet
    atoms.sort(key=lambda a: a[0], reverse=True)
    return atoms


_ATOMS = _duration_atoms()

# quarterLength of one tick.
_TICK_QL = Fraction(1, _QUARTER_TICKS)


def _split_ticks(ticks: int) -> list[Fraction]:
    """Decompose ``ticks`` into notatable quarterLengths (greedy)."""
    out: list[Fraction] = []
    remaining = ticks
    while remaining > 0:
        for atom_ticks, quarter_length in _ATOMS:
            if atom_ticks <= remaining:
                out.append(quarter_length)
                remaining -= atom_ticks
                break
        else:
            raise MusicXmlExportError(
                f"cannot represent {ticks} ticks as notatable durations"
            )
    return out


def _key_signature(key: str) -> m21key.Key:
    """Map a '<tonic> <mode>' key (e.g. 'A minor') to a music21 Key.

    Unknown or unparseable keys fall back to C major (as the gp5 exporter).
    """
    parts = key.strip().split()
    if len(parts) != 2 or not parts[0]:
        return m21key.Key("C")
    tonic, mode = parts
    mode = mode.lower()
    if mode not in ("major", "minor"):
        return m21key.Key("C")
    name = tonic[0].upper() + tonic[1:].replace("b", "-")
    try:
        return m21key.Key(name, mode)
    except Exception:
        return m21key.Key("C")


def _chord_symbol(label: str) -> m21harmony.ChordSymbol | None:
    """Build a chord symbol from a Harte label; None when not annotatable."""
    if not label or label == _NO_CHORD:
        return None
    root, _, quality = label.partition(":")
    if not root:
        return None
    figure = root[0].upper() + root[1:].replace("b", "-")
    figure += _HARTE_TO_FIGURE.get(quality, "")
    try:
        return m21harmony.ChordSymbol(figure)
    except Exception:
        return None


@dataclass
class _Segment:
    """A chord-to-be: simultaneous notes over one in-measure tick span."""

    start: int  # absolute ticks from measure 1, beat 1
    duration: int  # ticks, never crossing a measure boundary
    notes: list[tuple[int, int, Technique | None]]  # (string, fret, technique)
    chain: int  # id shared by the tied chunks of one original onset


@dataclass
class _PartPlan:
    """One TabScore resolved to tick segments grouped by measure."""

    score: TabScore
    segments_by_measure: dict[int, list[_Segment]] = field(default_factory=dict)
    chords_by_measure: dict[int, str] = field(default_factory=dict)
    last_measure: int = 1


def _grid_ticks(units: int, beat_ticks: int, grid: int, what: str) -> int:
    """Convert ``units`` subdivisions of a ``grid``-per-beat into ticks."""
    total = units * beat_ticks
    if grid < 1 or total % grid:
        raise MusicXmlExportError(
            f"{what}: {units} subdivisions of a {grid}-grid do not align "
            f"with the {beat_ticks}-tick beat"
        )
    return total // grid


def _plan_part(
    score: TabScore,
    grids: Sequence[int],
    beat_ticks: int,
    measure_ticks: int,
    measure_offset: int,
) -> _PartPlan:
    """Resolve a score's events into non-overlapping measure segments."""
    n_strings = len(score.tuning_midi)
    # start, duration, string, fret, technique
    onsets: list[tuple[int, int, int, int, Technique | None]] = []
    for index, (event, grid) in enumerate(zip(score.events, grids)):
        what = f"{score.instrument} event {index}"
        if not 1 <= event.string <= n_strings:
            raise MusicXmlExportError(
                f"{what}: string {event.string} outside 1..{n_strings}"
            )
        if event.fret < 0:
            raise MusicXmlExportError(f"{what}: negative fret {event.fret}")
        if event.duration_subdivisions < 1:
            raise MusicXmlExportError(f"{what}: duration must be >= 1 subdivision")
        start = (
            (event.measure - 1 + measure_offset) * measure_ticks
            + (event.beat - 1) * beat_ticks
            + _grid_ticks(event.subdivision, beat_ticks, grid, what)
        )
        duration = _grid_ticks(event.duration_subdivisions, beat_ticks, grid, what)
        onsets.append((start, duration, event.string, event.fret, event.technique))
    onsets.sort(key=lambda o: (o[0], o[2]))

    # Simultaneous onsets form one chord; it lasts their shortest duration.
    grouped: list[_Segment] = []
    for start, duration, string, fret, technique in onsets:
        if grouped and grouped[-1].start == start:
            grouped[-1].notes.append((string, fret, technique))
            grouped[-1].duration = min(grouped[-1].duration, duration)
        else:
            grouped.append(
                _Segment(start, duration, [(string, fret, technique)], len(grouped))
            )

    plan = _PartPlan(score=score)
    for current, nxt in zip(grouped, grouped[1:] + [None]):
        if nxt is not None:  # truncate at the next onset (single voice)
            current.duration = min(current.duration, nxt.start - current.start)
        # Split at measure boundaries; chunks share the chain id for ties.
        start, remaining = current.start, current.duration
        while remaining > 0:
            measure = start // measure_ticks + 1
            boundary = measure * measure_ticks
            chunk = min(remaining, boundary - start)
            plan.segments_by_measure.setdefault(measure, []).append(
                _Segment(start, chunk, current.notes, current.chain)
            )
            plan.last_measure = max(plan.last_measure, measure)
            start, remaining = start + chunk, remaining - chunk

    for chord in score.chords:
        if chord.label and chord.label != _NO_CHORD:
            measure = chord.measure + measure_offset
            plan.chords_by_measure[measure] = chord.label
            plan.last_measure = max(plan.last_measure, measure)
    return plan


def _append_rests(measure: m21stream.Measure, offset: int, ticks: int) -> None:
    """Fill ``ticks`` from in-measure tick ``offset`` with rests."""
    cursor = offset
    for quarter_length in _split_ticks(ticks):
        rest = m21note.Rest()
        rest.quarterLength = quarter_length
        measure.insert(cursor * _TICK_QL, rest)
        cursor += round(quarter_length * _QUARTER_TICKS)


def _make_element(
    pitches: Sequence[int],
    strings_frets: Sequence[tuple[int, int, Technique | None]],
    first: bool,
) -> m21note.NotRest:
    """One note or chord; string/fret indications go on a chain's first chunk."""
    if len(pitches) == 1:
        element: m21note.NotRest = m21note.Note()
        element.pitch.midi = pitches[0]
    else:
        m21_pitches = []
        for value in pitches:
            p = m21pitch.Pitch()
            p.midi = value
            m21_pitches.append(p)
        element = m21chord.Chord(m21_pitches)
    if first and len(strings_frets) == 1:
        string, fret, _ = strings_frets[0]
        element.articulations.append(m21articulations.StringIndication(string))
        element.articulations.append(m21articulations.FretIndication(fret))
    if first:
        for _, _, technique in strings_frets:
            if technique is not None and technique.kind == TECHNIQUE_BEND:
                element.articulations.append(
                    m21articulations.FretBend(
                        bendAlter=m21interval.ChromaticInterval(
                            technique.bend_semitones
                        )
                    )
                )
    return element


def _link_spanner(technique: Technique | None, origin, target):
    """Spanner from ``origin`` to ``target`` for a link technique, else None."""
    if technique is None:
        return None
    if technique.kind == TECHNIQUE_SLIDE:
        glissando = m21spanner.Glissando(origin, target)
        glissando.slideType = "continuous"
        glissando.lineType = "solid"
        return glissando
    if technique.kind == TECHNIQUE_HAMMER_ON:
        return m21articulations.HammerOn(origin, target)
    if technique.kind == TECHNIQUE_PULL_OFF:
        return m21articulations.PullOff(origin, target)
    return None


def _build_part(
    plan: _PartPlan,
    total_measures: int,
    measure_ticks: int,
    numerator: int,
    denominator: int,
    include_tempo: bool,
) -> m21stream.Part:
    """Write a plan's measures: notes in order, rests filling every gap."""
    score = plan.score
    n_strings = len(score.tuning_midi)
    part = m21stream.Part()
    part.partName = score.instrument
    chains: dict[int, list[m21note.NotRest]] = {}
    chain_notes: dict[int, list[tuple[int, int, Technique | None]]] = {}

    for number in range(1, total_measures + 1):
        measure = m21stream.Measure(number=number)
        if number == 1:
            measure.insert(0, _key_signature(score.key))
            measure.insert(0, m21meter.TimeSignature(f"{numerator}/{denominator}"))
            if include_tempo and score.tempo_bpm > 0:
                measure.insert(
                    0, m21tempo.MetronomeMark(number=round(score.tempo_bpm, 2))
                )
        symbol = _chord_symbol(plan.chords_by_measure.get(number, ""))
        if symbol is not None:
            measure.insert(0, symbol)

        measure_start = (number - 1) * measure_ticks
        cursor = measure_start
        for segment in plan.segments_by_measure.get(number, []):
            if segment.start > cursor:
                _append_rests(measure, cursor - measure_start, segment.start - cursor)
            pitches = [
                score.tuning_midi[n_strings - string] + fret + score.capo_fret
                for string, fret, _ in segment.notes
            ]
            offset = segment.start - measure_start
            chain = chains.setdefault(segment.chain, [])
            chain_notes.setdefault(segment.chain, segment.notes)
            for quarter_length in _split_ticks(segment.duration):
                element = _make_element(pitches, segment.notes, first=not chain)
                element.quarterLength = quarter_length
                measure.insert(offset * _TICK_QL, element)
                chain.append(element)
                offset += round(quarter_length * _QUARTER_TICKS)
            cursor = segment.start + segment.duration
        if cursor < measure_start + measure_ticks:
            _append_rests(
                measure,
                cursor - measure_start,
                measure_start + measure_ticks - cursor,
            )
        part.append(measure)

    for chain in chains.values():  # tie-chain the chunks of each onset
        if len(chain) > 1:
            chain[0].tie = m21tie.Tie("start")
            for element in chain[1:-1]:
                element.tie = m21tie.Tie("continue")
            chain[-1].tie = m21tie.Tie("stop")

    # Link techniques span from the origin's last element to the first
    # element of the next onset on the same string (chain ids follow onsets).
    ordered = sorted(chain_notes)
    for position, chain_id in enumerate(ordered):
        for string, _, technique in chain_notes[chain_id]:
            target_id = next(
                (
                    later
                    for later in ordered[position + 1 :]
                    if any(s == string for s, _, _ in chain_notes[later])
                ),
                None,
            )
            if target_id is None:
                continue
            spanner = _link_spanner(
                technique, chains[chain_id][-1], chains[target_id][0]
            )
            if spanner is not None:
                part.insert(0, spanner)
    return part


def export_musicxml(
    scores: TabScore | Sequence[TabScore],
    output_path: str | Path,
    beat_grids: Sequence[Sequence[int]] | None = None,
    default_subdivisions_in_beat: int = 4,
    title: str = "",
) -> Path:
    """Write one or more ``TabScore`` as a MusicXML file.

    ``beat_grids`` runs parallel to ``scores``; each entry runs parallel to
    that score's ``events`` and gives the note's subdivisions-per-beat
    (``QuantizedNote.subdivisions_in_beat``: 4 straight, 3 triplet). When
    ``None`` (or for any missing entry) ``default_subdivisions_in_beat``
    applies. All scores must share the same time signature (as the gp5
    exporter, so all exporters behave uniformly). Returns the path of the
    written file.
    """
    score_list = [scores] if isinstance(scores, TabScore) else list(scores)
    if not score_list:
        raise MusicXmlExportError("no TabScore to export")
    if beat_grids is not None and len(beat_grids) != len(score_list):
        raise MusicXmlExportError(
            f"beat_grids length {len(beat_grids)} does not match "
            f"score count {len(score_list)}"
        )

    numerator, denominator = score_list[0].time_signature
    for score in score_list:
        if score.time_signature != [numerator, denominator]:
            raise MusicXmlExportError(
                "all scores must share one time signature; got "
                f"{score.time_signature} vs {[numerator, denominator]}"
            )
    if numerator < 1 or denominator < 1 or _WHOLE_TICKS % denominator:
        raise MusicXmlExportError(
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

    plans: list[_PartPlan] = []
    for index, score in enumerate(score_list):
        grids = list(beat_grids[index]) if beat_grids is not None else []
        if len(grids) < len(score.events):
            grids += [default_subdivisions_in_beat] * (len(score.events) - len(grids))
        plans.append(
            _plan_part(score, grids, beat_ticks, measure_ticks, measure_offset)
        )
    total_measures = max(plan.last_measure for plan in plans)

    m21_score = m21stream.Score()
    if title:
        m21_score.metadata = m21metadata.Metadata(title=title)
    for index, plan in enumerate(plans):
        m21_score.append(
            _build_part(
                plan,
                total_measures,
                measure_ticks,
                numerator,
                denominator,
                include_tempo=index == 0,
            )
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m21_score.write("musicxml", fp=str(output_path))
    return output_path
