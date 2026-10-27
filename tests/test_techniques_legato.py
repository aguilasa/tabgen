"""Hammer-on / pull-off detection from weak onsets (synthetic cases)."""

from dataclasses import replace

import pytest

from tabgen.core.models import (
    TECHNIQUE_BEND,
    TECHNIQUE_HAMMER_ON,
    TECHNIQUE_PULL_OFF,
    Note,
    TabNote,
    Technique,
)
from tabgen.core.techniques.legato import LegatoConfig, detect_legato

# Open pitches by guitarist string number (1 = high E).
OPEN = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}


def _pair(string, fret, start, end, velocity, measure=1):
    """Build a parallel (TabNote, Note) for a fretted note."""
    tab = TabNote(
        string=string,
        fret=fret,
        measure=measure,
        beat=1,
        subdivision=0,
        duration_subdivisions=1,
        start_s=start,
        end_s=end,
    )
    note = Note(
        pitch_midi=OPEN[string] + fret, start_s=start, end_s=end, velocity=velocity
    )
    return tab, note


def _run(pairs, config=None):
    events = [p[0] for p in pairs]
    notes = [p[1] for p in pairs]
    return detect_legato(events, notes, config)


def test_weak_contiguous_higher_fret_is_hammer_on():
    out = _run([_pair(3, 5, 0.0, 0.25, 0.8), _pair(3, 7, 0.25, 0.5, 0.8 * 0.3)])
    assert out[0].technique == Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)
    assert out[1].technique is None


def test_weak_contiguous_lower_fret_is_pull_off():
    out = _run([_pair(3, 7, 0.0, 0.25, 0.8), _pair(3, 5, 0.25, 0.5, 0.8 * 0.3)])
    assert out[0].technique == Technique(kind=TECHNIQUE_PULL_OFF, target_fret=5)
    assert out[1].technique is None


def test_strong_second_note_is_not_legato():
    out = _run([_pair(3, 5, 0.0, 0.25, 0.8), _pair(3, 7, 0.25, 0.5, 0.8)])
    assert [e.technique for e in out] == [None, None]


def test_gap_above_threshold_is_not_legato():
    gap = LegatoConfig().max_gap_s + 0.02
    out = _run([_pair(3, 5, 0.0, 0.25, 0.8), _pair(3, 7, 0.25 + gap, 0.5, 0.24)])
    assert [e.technique for e in out] == [None, None]


def test_other_string_is_not_legato():
    out = _run([_pair(3, 5, 0.0, 0.25, 0.8), _pair(2, 7, 0.25, 0.5, 0.24)])
    assert [e.technique for e in out] == [None, None]


def test_first_note_of_measure_after_rest_is_never_legato():
    # Measure 1 ends with fret 5 then a rest; measure 2 opens with a weak
    # fret 7 on the same string (120 bpm, 4/4: measure 2 starts at 2.0 s).
    out = _run(
        [
            _pair(3, 5, 1.5, 1.75, 0.8, measure=1),
            _pair(3, 7, 2.0, 2.25, 0.2, measure=2),
        ]
    )
    assert [e.technique for e in out] == [None, None]


def test_interval_above_max_is_not_legato():
    out = _run([_pair(3, 2, 0.0, 0.25, 0.8), _pair(3, 9, 0.25, 0.5, 0.2)])
    assert [e.technique for e in out] == [None, None]


def test_same_fret_is_not_legato():
    out = _run([_pair(3, 5, 0.0, 0.25, 0.8), _pair(3, 5, 0.25, 0.5, 0.2)])
    assert [e.technique for e in out] == [None, None]


def test_small_overlap_still_counts_as_contiguous():
    out = _run([_pair(3, 5, 0.0, 0.27, 0.8), _pair(3, 7, 0.25, 0.5, 0.2)])
    assert out[0].technique.kind == TECHNIQUE_HAMMER_ON


def test_chain_hammer_then_pull_and_other_string_in_between():
    # 5h7p5 on string 3 while string 1 rings an unrelated note.
    out = _run(
        [
            _pair(3, 5, 0.0, 0.25, 0.9),
            _pair(1, 0, 0.1, 0.6, 0.9),
            _pair(3, 7, 0.25, 0.5, 0.4),
            _pair(3, 5, 0.5, 0.75, 0.2),
        ]
    )
    assert out[0].technique == Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)
    assert out[1].technique is None
    assert out[2].technique == Technique(kind=TECHNIQUE_PULL_OFF, target_fret=5)
    assert out[3].technique is None


def test_unsorted_input_keeps_order():
    pairs = [_pair(3, 7, 0.25, 0.5, 0.24), _pair(3, 5, 0.0, 0.25, 0.8)]
    out = _run(pairs)
    assert out[0].fret == 7 and out[0].technique is None
    assert out[1].technique == Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)


def test_existing_technique_is_not_overwritten_and_inputs_untouched():
    bend = Technique(kind=TECHNIQUE_BEND, bend_semitones=1.0)
    origin, origin_note = _pair(3, 5, 0.0, 0.25, 0.8)
    origin = replace(origin, technique=bend)
    target, target_note = _pair(3, 7, 0.25, 0.5, 0.24)
    events = [origin, target]
    out = detect_legato(events, [origin_note, target_note])
    assert out[0].technique == bend
    assert events[0].technique is bend and events[1].technique is None


def test_does_not_mutate_inputs():
    events, notes = zip(*[_pair(3, 5, 0.0, 0.25, 0.8), _pair(3, 7, 0.25, 0.5, 0.24)])
    out = detect_legato(events, notes)
    assert out[0] is not events[0]
    assert events[0].technique is None


def test_config_ratio_is_honored():
    pairs = [_pair(3, 5, 0.0, 0.25, 0.8), _pair(3, 7, 0.25, 0.5, 0.24)]
    out = _run(pairs, LegatoConfig(max_amplitude_ratio=0.2))
    assert out[0].technique is None


def test_length_mismatch_raises():
    tab, note = _pair(3, 5, 0.0, 0.25, 0.8)
    with pytest.raises(ValueError):
        detect_legato([tab], [note, note])


def test_empty_input():
    assert detect_legato([], []) == []
