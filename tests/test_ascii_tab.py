"""ASCII tab export: golden byte-for-byte match and system/line layout."""

import re
from pathlib import Path

import pytest

from tabgen.core.export.ascii_tab import (
    AsciiTabExportError,
    export_ascii_tab,
    render_ascii_tab,
)
from tabgen.core.models import (
    BASS_STANDARD_TUNING,
    SLIDE_DOWN,
    SLIDE_UP,
    TECHNIQUE_BEND,
    TECHNIQUE_HAMMER_ON,
    TECHNIQUE_PULL_OFF,
    TECHNIQUE_SLIDE,
    MeasureChord,
    TabNote,
    TabScore,
    Technique,
)

GOLDEN = Path(__file__).parent / "golden" / "ascii_guitar_riff.txt"

# A tab string line: a pitch-class label then |cells|cells|...
STRING_LINE = re.compile(r"^[A-G]#? *(\|[0-9-]+)+\|$")


def _note(string, fret, measure, beat, subdivision=0, duration=4):
    return TabNote(
        string=string,
        fret=fret,
        measure=measure,
        beat=beat,
        subdivision=subdivision,
        duration_subdivisions=duration,
        start_s=0.0,
        end_s=0.5,
    )


def _golden_riff():
    """1-measure guitar riff pinned by tests/golden/ascii_guitar_riff.txt."""
    return TabScore(
        instrument="guitar",
        tempo_bpm=120.0,
        key="E minor",
        time_signature=[4, 4],
        events=[
            _note(6, 0, measure=1, beat=1),
            _note(5, 2, measure=1, beat=1),
            _note(4, 2, measure=1, beat=2, duration=2),
            _note(3, 0, measure=1, beat=3, duration=2),
            _note(1, 3, measure=1, beat=4, subdivision=2, duration=2),
        ],
    )


def test_golden_guitar_riff_matches_bytes(tmp_path):
    path = export_ascii_tab(_golden_riff(), tmp_path / "riff.txt")
    assert path.read_bytes() == GOLDEN.read_bytes()
    assert render_ascii_tab(_golden_riff()).encode("utf-8") == GOLDEN.read_bytes()


def test_guitar_has_six_string_lines_per_system():
    text = render_ascii_tab(_golden_riff())
    assert sum(1 for line in text.splitlines() if STRING_LINE.match(line)) == 6


def test_bass_has_four_string_lines_per_system():
    bass = TabScore(
        instrument="bass",
        tuning_midi=list(BASS_STANDARD_TUNING),
        tempo_bpm=90.0,
        time_signature=[4, 4],
        events=[
            _note(4, 0, measure=1, beat=1),
            _note(3, 2, measure=2, beat=1),
            _note(2, 12, measure=5, beat=3),
        ],
    )
    text = render_ascii_tab(bass, measures_per_line=4)
    lines = text.splitlines()
    string_lines = [line for line in lines if STRING_LINE.match(line)]
    # 5 measures wrapped at 4 per line -> 2 systems of 4 string lines each.
    assert len(string_lines) == 8
    assert string_lines[0].count("|") == 5  # 4 measures in the first system
    assert string_lines[4].count("|") == 2  # 1 measure in the second system
    # Labels top-down are the open strings high-to-low: G D A E.
    assert [line[0] for line in string_lines[:4]] == ["G", "D", "A", "E"]
    # Two-digit fret stays aligned: measure width is uniform.
    widths = {len(line) for line in string_lines[4:]}
    assert len(widths) == 1 and "12-" in string_lines[5]


def test_header_chords_and_triplet_columns():
    score = TabScore(
        instrument="guitar",
        tempo_bpm=132.5,
        key="A minor",
        capo_fret=2,
        time_signature=[4, 4],
        events=[
            # Triplet eighths (3-grid) flattened onto the 4-cell beat layout.
            _note(2, 5, measure=1, beat=1, subdivision=0, duration=1),
            _note(2, 7, measure=1, beat=1, subdivision=1, duration=1),
            _note(2, 8, measure=1, beat=1, subdivision=2, duration=1),
        ],
        chords=[MeasureChord(measure=1, label="A:min"), MeasureChord(2, "N")],
    )
    text = render_ascii_tab(score, beat_grids=[[3, 3, 3]])
    header = text.splitlines()[1]
    assert "Capo: 2" in header
    assert "BPM: 132.5" in header
    assert "Key: A minor" in header
    assert "Time: 4/4" in header
    assert "A:min" in text
    assert "N" not in [w for line in text.splitlines() for w in line.split()]
    b_line = next(line for line in text.splitlines() if line.startswith("B"))
    # Columns round(0*4/3)=0, round(1*4/3)=1, round(2*4/3)=3 inside beat 1.
    assert b_line.startswith("B|5-7---8-")


def test_rejects_empty_scores_and_bad_events():
    with pytest.raises(AsciiTabExportError, match="no TabScore"):
        render_ascii_tab([])
    bad_string = TabScore(events=[_note(7, 0, measure=1, beat=1)])
    with pytest.raises(AsciiTabExportError, match="string 7"):
        render_ascii_tab(bad_string)
    bad_beat = TabScore(events=[_note(1, 0, measure=1, beat=5)])
    with pytest.raises(AsciiTabExportError, match="beat 5"):
        render_ascii_tab(bad_beat)


TECHNIQUES_GOLDEN = Path(__file__).parent / "golden" / "ascii_techniques.txt"


def _linked(string, fret, measure, beat, subdivision, technique=None):
    note = _note(string, fret, measure, beat, subdivision=subdivision, duration=1)
    note.technique = technique
    return note


def _techniques_riff():
    """2-measure lick pinned by tests/golden/ascii_techniques.txt: a whole-step
    bend, slides up and down, a hammer-on and a pull-off."""
    return TabScore(
        instrument="guitar",
        tempo_bpm=100.0,
        key="A minor",
        time_signature=[4, 4],
        events=[
            _linked(3, 7, 1, 1, 0, Technique(kind=TECHNIQUE_BEND, bend_semitones=2.0)),
            _linked(
                2, 5, 1, 2, 0,
                Technique(
                    kind=TECHNIQUE_SLIDE, slide_direction=SLIDE_UP, target_fret=7
                ),
            ),
            _linked(2, 7, 1, 2, 1),
            _linked(
                2, 7, 1, 3, 0,
                Technique(
                    kind=TECHNIQUE_SLIDE, slide_direction=SLIDE_DOWN, target_fret=5
                ),
            ),
            _linked(2, 5, 1, 3, 1),
            _linked(1, 5, 2, 1, 0, Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)),
            _linked(1, 7, 2, 1, 1),
            _linked(1, 7, 2, 2, 0, Technique(kind=TECHNIQUE_PULL_OFF, target_fret=5)),
            _linked(1, 5, 2, 2, 1),
        ],
    )


def test_golden_techniques_match_bytes(tmp_path):
    path = export_ascii_tab(_techniques_riff(), tmp_path / "lick.txt")
    assert path.read_bytes() == TECHNIQUES_GOLDEN.read_bytes()


def test_technique_marks_follow_the_origin_fret():
    lines = render_ascii_tab(_techniques_riff()).splitlines()
    g_line = next(line for line in lines if line.startswith("G|"))
    b_line = next(line for line in lines if line.startswith("B|"))
    e_line = next(line for line in lines if line.startswith("E|") and "h" in line)
    assert g_line.startswith("G|7b9-")
    assert "5/--7" in b_line and "7\\--5" in b_line
    assert "5h--7" in e_line and "7p--5" in e_line


def test_link_marks_touch_the_next_fret_without_bends():
    score = TabScore(
        events=[
            _linked(1, 5, 1, 1, 0, Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)),
            _linked(1, 7, 1, 1, 1, Technique(kind=TECHNIQUE_PULL_OFF, target_fret=5)),
            _linked(1, 5, 1, 1, 2),
        ]
    )
    e_line = render_ascii_tab(score).splitlines()[3]
    assert e_line.startswith("E|5h7p5-")
