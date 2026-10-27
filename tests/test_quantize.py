"""Tests for the quantization stage (Note times -> beat-grid positions)."""

import random

import pytest

from tabgen.core.export.quantize import quantize_notes
from tabgen.core.models import Note

# 120 BPM: one beat every 0.5 s; a sixteenth is 0.125 s.
BEAT_S = 0.5
SIXTEENTH_S = BEAT_S / 4


def _grid_120bpm_4_4(measures: int = 4) -> tuple[list[float], list[float]]:
    """Beat and downbeat times for ``measures`` measures of 4/4 at 120 BPM."""
    beats = [i * BEAT_S for i in range(measures * 4 + 1)]
    downbeats = [m * 4 * BEAT_S for m in range(measures + 1)]
    return beats, downbeats


def test_jittered_sixteenths_return_to_their_positions() -> None:
    beats, downbeats = _grid_120bpm_4_4(measures=4)
    rng = random.Random(42)

    expected: list[tuple[int, int, int]] = []
    notes: list[Note] = []
    for measure in range(1, 5):
        for beat in range(1, 5):
            for subdivision in range(4):
                t = ((measure - 1) * 4 + (beat - 1)) * BEAT_S
                t += subdivision * SIXTEENTH_S
                start = t + rng.uniform(-0.02, 0.02)
                notes.append(Note(pitch_midi=60, start_s=start, end_s=start + 0.1))
                expected.append((measure, beat, subdivision))

    result = quantize_notes(notes, beats, downbeats)

    got = [(q.measure, q.beat, q.subdivision) for q in result]
    assert got == expected
    assert all(q.subdivisions_in_beat == 4 for q in result)


def test_three_equally_spaced_notes_quantize_as_triplet() -> None:
    beats, downbeats = _grid_120bpm_4_4(measures=1)
    # Three notes evenly spread over the second beat (0.5 s .. 1.0 s).
    notes = [
        Note(
            pitch_midi=60 + i,
            start_s=BEAT_S + i * BEAT_S / 3,
            end_s=BEAT_S + (i + 1) * BEAT_S / 3,
        )
        for i in range(3)
    ]

    result = quantize_notes(notes, beats, downbeats)

    assert [(q.measure, q.beat) for q in result] == [(1, 2)] * 3
    assert [q.subdivision for q in result] == [0, 1, 2]
    assert all(q.subdivisions_in_beat == 3 for q in result)


def test_variable_tempo_keeps_each_note_on_the_correct_beat() -> None:
    # Increasing inter-beat intervals: 0.5, 0.6, 0.7, 0.8, 0.9 s.
    beats = [0.0, 0.5, 1.1, 1.8, 2.6, 3.5]
    downbeats = [0.0]  # single downbeat: 4/4 assumed

    notes = [Note(pitch_midi=60, start_s=t, end_s=t + 0.05) for t in beats[:5]]
    # Midpoint of the third interval (1.1 s .. 1.8 s) -> subdivision 2.
    notes.append(Note(pitch_midi=72, start_s=1.45, end_s=1.55))

    result = quantize_notes(notes, beats, downbeats)

    on_beats = [q for q in result if q.pitch_midi == 60]
    assert [(q.measure, q.beat, q.subdivision) for q in on_beats] == [
        (1, 1, 0),
        (1, 2, 0),
        (1, 3, 0),
        (1, 4, 0),
        (2, 1, 0),
    ]
    mid = next(q for q in result if q.pitch_midi == 72)
    assert (mid.measure, mid.beat, mid.subdivision) == (1, 3, 2)


def test_anacrusis_notes_land_in_measure_zero() -> None:
    beats = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    downbeats = [0.5, 2.5]  # one pickup beat before the first downbeat

    notes = [
        Note(pitch_midi=60, start_s=0.0, end_s=0.2),  # pickup beat
        Note(pitch_midi=62, start_s=0.25, end_s=0.4),  # its third sixteenth
        Note(pitch_midi=64, start_s=0.5, end_s=0.7),  # first downbeat
    ]

    result = quantize_notes(notes, beats, downbeats)

    assert [(q.measure, q.beat, q.subdivision) for q in result] == [
        (0, 4, 0),
        (0, 4, 2),
        (1, 1, 0),
    ]


def test_times_outside_the_grid_extrapolate_the_edge_intervals() -> None:
    beats = [0.0, 0.5, 1.0]
    downbeats = [0.0]

    notes = [
        # One sixteenth before the first beat: virtual pickup position.
        Note(pitch_midi=60, start_s=-0.125, end_s=-0.03),
        # Half a (virtual) beat after the last beat time.
        Note(pitch_midi=62, start_s=1.25, end_s=1.3),
    ]

    result = quantize_notes(notes, beats, downbeats)

    before = next(q for q in result if q.pitch_midi == 60)
    after = next(q for q in result if q.pitch_midi == 62)
    assert (before.measure, before.beat, before.subdivision) == (0, 4, 3)
    assert (after.measure, after.beat, after.subdivision) == (1, 3, 2)


def test_onset_near_the_next_beat_carries_over_to_subdivision_zero() -> None:
    beats, downbeats = _grid_120bpm_4_4(measures=1)

    # 10 ms before the second beat: closer to it than to any sixteenth.
    result = quantize_notes(
        [Note(pitch_midi=60, start_s=0.49, end_s=0.6)], beats, downbeats
    )

    (q,) = result
    assert (q.measure, q.beat, q.subdivision) == (1, 2, 0)


def test_duration_is_floored_at_one_subdivision() -> None:
    beats, downbeats = _grid_120bpm_4_4(measures=1)

    notes = [
        Note(pitch_midi=60, start_s=0.0, end_s=0.01),  # far below one sixteenth
        Note(pitch_midi=62, start_s=0.5, end_s=1.0),  # exactly one beat
    ]
    result = quantize_notes(notes, beats, downbeats)

    short = next(q for q in result if q.pitch_midi == 60)
    full_beat = next(q for q in result if q.pitch_midi == 62)
    assert short.duration_subdivisions == 1
    assert full_beat.duration_subdivisions == 4


def test_fewer_than_two_beats_is_rejected() -> None:
    with pytest.raises(ValueError):
        quantize_notes([Note(pitch_midi=60, start_s=0.0, end_s=0.1)], [0.0], [0.0])
