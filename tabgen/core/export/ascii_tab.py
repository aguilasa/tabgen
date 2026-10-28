"""Render TabScore(s) as plain-text (ASCII) tablature.

Format (tabgen's own; the golden test under ``tests/`` pins the bytes):

- Per score: a header with the instrument name, tuning (low to high,
  scientific pitch), capo (when set), BPM, key (when known) and time
  signature, then systems of ``measures_per_line`` measures.
- One line per string, string 1 (highest-pitched) on top, so a guitar shows
  6 lines per system and a bass 4; labels are the open-string pitch classes.
  Measures are delimited by ``|``.
- Each beat occupies ``default_subdivisions_in_beat`` fixed-width cells
  (fret left-aligned, padded with ``-``), so frets align per measure.
- ``beat_grids`` follows the gp5 exporter convention (per score, parallel to
  ``events``, each note's subdivisions-per-beat: 4 straight / 3 triplet) but
  only affects column mapping: a note on a ``g``-grid at subdivision ``s``
  lands on cell ``round(s * cells / g)`` of its beat — triplets are
  flattened onto the straight column layout. Only onsets are drawn
  (durations are not rendered); when two onsets collide on one string and
  cell, the later event wins.
- Techniques use the usual tab marks on the ORIGIN note's cell: a bend is
  written ``<fret>b<target>`` with target = fret + ``bend_semitones``
  (``7b9``; a quarter-tone step shows as ``7b8.5``); a slide adds ``/``
  (up) or ``\\`` (down), a hammer-on ``h`` and a pull-off ``p`` right after
  the fret, so the next note on the string reads ``5/7``, ``7\\5``,
  ``5h7``, ``7p5`` when it is in the next cell (cell padding ``-`` sits in
  between otherwise). The cell width fits the longest fret or bend token
  plus one character, which always leaves room for a link mark; a score
  without techniques renders exactly as before.
- A chord-label line (Harte labels, measure-aligned) tops any system that
  has chord annotations; ``N`` (no chord) is skipped.

This module is pure core: no print/typer/rich.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from tabgen.core.models import (
    SLIDE_UP,
    TECHNIQUE_BEND,
    TECHNIQUE_HAMMER_ON,
    TECHNIQUE_PULL_OFF,
    TECHNIQUE_SLIDE,
    TabNote,
    TabScore,
)

# Pitch-class names used for string labels and tuning (sharps spelling).
_PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Chord label meaning "no chord" in Harte notation; never annotated.
_NO_CHORD = "N"


class AsciiTabExportError(RuntimeError):
    """Raised when TabScores cannot be rendered as ASCII tablature."""


def _pitch_class(midi: int) -> str:
    """Pitch-class name of a MIDI pitch, e.g. 64 -> 'E'."""
    return _PITCH_NAMES[midi % 12]


def _pitch_name(midi: int) -> str:
    """Scientific pitch name of a MIDI pitch, e.g. 64 -> 'E4'."""
    return f"{_PITCH_NAMES[midi % 12]}{midi // 12 - 1}"


def _bend_token(event: TabNote) -> str:
    """``<fret>b<target>`` of a bend (target fret = fret + bend semitones)."""
    return f"{event.fret}b{event.fret + event.technique.bend_semitones:g}"


def _cell_token(event: TabNote) -> str:
    """Text of an onset cell: fret plus its technique mark (see docstring)."""
    technique = event.technique
    if technique is None:
        return str(event.fret)
    if technique.kind == TECHNIQUE_BEND:
        return _bend_token(event)
    if technique.kind == TECHNIQUE_SLIDE:
        mark = "/" if technique.slide_direction == SLIDE_UP else "\\"
        return f"{event.fret}{mark}"
    if technique.kind == TECHNIQUE_HAMMER_ON:
        return f"{event.fret}h"
    if technique.kind == TECHNIQUE_PULL_OFF:
        return f"{event.fret}p"
    return str(event.fret)


def _header_lines(score: TabScore, numerator: int, denominator: int) -> list[str]:
    """Instrument name plus tuning/capo/BPM/key/time-signature line."""
    fields = [
        "Tuning: "
        + " ".join(_pitch_name(p) for p in score.tuning_midi)
        + " (low to high)"
    ]
    if score.capo_fret:
        fields.append(f"Capo: {score.capo_fret}")
    if score.tempo_bpm > 0:
        fields.append(f"BPM: {score.tempo_bpm:g}")
    if score.key:
        fields.append(f"Key: {score.key}")
    fields.append(f"Time: {numerator}/{denominator}")
    return [score.instrument.capitalize(), " | ".join(fields)]


def _render_score(
    score: TabScore,
    grids: Sequence[int],
    measure_offset: int,
    cells_per_beat: int,
    measures_per_line: int,
) -> str:
    """Render one score: header plus wrapped tab systems."""
    n_strings = len(score.tuning_midi)
    numerator, denominator = score.time_signature
    if numerator < 1 or denominator < 1:
        raise AsciiTabExportError(
            f"unsupported time signature {numerator}/{denominator}"
        )
    measure_cells = numerator * cells_per_beat

    # (measure, string) -> column -> cell token; columns are straight-grid
    # cells.
    frets: dict[tuple[int, int], dict[int, str]] = {}
    last_measure = 1
    max_token = 1
    for index, (event, grid) in enumerate(zip(score.events, grids)):
        what = f"{score.instrument} event {index}"
        if not 1 <= event.string <= n_strings:
            raise AsciiTabExportError(
                f"{what}: string {event.string} outside 1..{n_strings}"
            )
        if event.fret < 0:
            raise AsciiTabExportError(f"{what}: negative fret {event.fret}")
        if not 1 <= event.beat <= numerator:
            raise AsciiTabExportError(
                f"{what}: beat {event.beat} outside 1..{numerator}"
            )
        if grid < 1 or not 0 <= event.subdivision < grid:
            raise AsciiTabExportError(
                f"{what}: subdivision {event.subdivision} outside the "
                f"{grid}-grid beat"
            )
        measure = event.measure + measure_offset
        column = (event.beat - 1) * cells_per_beat + min(
            cells_per_beat - 1, round(event.subdivision * cells_per_beat / grid)
        )
        frets.setdefault((measure, event.string), {})[column] = _cell_token(event)
        last_measure = max(last_measure, measure)
        # Link marks (one char) live in the +1 padding; bend tokens count whole.
        bend = event.technique is not None and event.technique.kind == TECHNIQUE_BEND
        max_token = max(
            max_token, len(_bend_token(event)) if bend else len(str(event.fret))
        )

    chords = {
        chord.measure + measure_offset: chord.label
        for chord in score.chords
        if chord.label and chord.label != _NO_CHORD
    }
    if chords:
        last_measure = max(last_measure, max(chords))

    cell_width = max(2, max_token + 1)
    measure_width = measure_cells * cell_width
    labels = [
        _pitch_class(score.tuning_midi[n_strings - s])
        for s in range(1, n_strings + 1)
    ]
    label_width = max(len(label) for label in labels)

    lines = _header_lines(score, numerator, denominator)
    for first in range(1, last_measure + 1, measures_per_line):
        lines.append("")
        system = range(first, min(first + measures_per_line, last_measure + 1))
        if any(measure in chords for measure in system):
            chord_line = " " * label_width
            for measure in system:
                label = chords.get(measure, "")
                chord_line += " " + label.ljust(measure_width)[:measure_width]
            lines.append(chord_line.rstrip())
        for string, label in enumerate(labels, start=1):
            line = label.ljust(label_width)
            for measure in system:
                columns = frets.get((measure, string), {})
                line += "|" + "".join(
                    columns[c].ljust(cell_width, "-")
                    if c in columns
                    else "-" * cell_width
                    for c in range(measure_cells)
                )
            lines.append(line + "|")
    return "\n".join(lines)


def render_ascii_tab(
    scores: TabScore | Sequence[TabScore],
    beat_grids: Sequence[Sequence[int]] | None = None,
    default_subdivisions_in_beat: int = 4,
    measures_per_line: int = 4,
) -> str:
    """Render one or more ``TabScore`` as an ASCII tablature string.

    ``beat_grids`` follows the gp5 exporter convention (see module
    docstring). Scores are rendered as sections separated by a blank line;
    the result always ends with a newline.
    """
    score_list = [scores] if isinstance(scores, TabScore) else list(scores)
    if not score_list:
        raise AsciiTabExportError("no TabScore to render")
    if beat_grids is not None and len(beat_grids) != len(score_list):
        raise AsciiTabExportError(
            f"beat_grids length {len(beat_grids)} does not match "
            f"score count {len(score_list)}"
        )
    if default_subdivisions_in_beat < 1:
        raise AsciiTabExportError("default_subdivisions_in_beat must be >= 1")
    if measures_per_line < 1:
        raise AsciiTabExportError("measures_per_line must be >= 1")

    # Anacrusis measures (<= 0) shift right so the tab starts at measure 1.
    min_measure = min(
        (event.measure for score in score_list for event in score.events),
        default=1,
    )
    measure_offset = max(0, 1 - min_measure)

    sections: list[str] = []
    for index, score in enumerate(score_list):
        grids = list(beat_grids[index]) if beat_grids is not None else []
        if len(grids) < len(score.events):
            grids += [default_subdivisions_in_beat] * (len(score.events) - len(grids))
        sections.append(
            _render_score(
                score,
                grids,
                measure_offset,
                default_subdivisions_in_beat,
                measures_per_line,
            )
        )
    return "\n\n".join(sections) + "\n"


def export_ascii_tab(
    scores: TabScore | Sequence[TabScore],
    output_path: str | Path,
    beat_grids: Sequence[Sequence[int]] | None = None,
    default_subdivisions_in_beat: int = 4,
    measures_per_line: int = 4,
) -> Path:
    """Write one or more ``TabScore`` as an ASCII tablature text file.

    Same parameters as :func:`render_ascii_tab`; the file is UTF-8 with LF
    newlines. Returns the path of the written file.
    """
    text = render_ascii_tab(
        scores,
        beat_grids=beat_grids,
        default_subdivisions_in_beat=default_subdivisions_in_beat,
        measures_per_line=measures_per_line,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    return output_path
