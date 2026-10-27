"""Bend/slide detection on synthetic Basic Pitch bend curves."""

from __future__ import annotations

import math
import random

import pytest

from tabgen.core.models import (
    SLIDE_DOWN,
    SLIDE_UP,
    TECHNIQUE_BEND,
    TECHNIQUE_HAMMER_ON,
    TECHNIQUE_SLIDE,
    Note,
    TabNote,
    Technique,
)
from tabgen.core.techniques import BASIC_PITCH_FPS, BendConfig, detect_bends_and_slides

BINS = 3  # Basic Pitch bins per semitone


def _event(string: int, fret: int, start: float, end: float) -> TabNote:
    return TabNote(
        string=string,
        fret=fret,
        measure=1,
        beat=1,
        subdivision=0,
        duration_subdivisions=1,
        start_s=start,
        end_s=end,
    )


def _note(pitch: int, start: float, end: float, bends: list[int] | None) -> Note:
    return Note(pitch_midi=pitch, start_s=start, end_s=end, bends=bends)


def _bend_curve(peak_bins: int, release: bool = False) -> list[int]:
    """Picked at pitch, rises to ``peak_bins`` and holds (optionally releases)."""
    rise = [round(peak_bins * k / 10) for k in range(10)]
    curve = [0] * 8 + rise + [peak_bins] * 30
    if release:
        curve += list(reversed(rise)) + [0] * 8
    return curve


def _vibrato() -> list[int]:
    """+-1 bin (1/3 semitone) at ~5.5 Hz for one second."""
    return [round(math.sin(2 * math.pi * 5.5 * i / BASIC_PITCH_FPS)) for i in range(86)]


def _single(bends: list[int] | None, config: BendConfig | None = None) -> TabNote:
    duration = len(bends or [0]) / BASIC_PITCH_FPS
    events = [_event(3, 7, 0.0, duration)]
    notes = [_note(62, 0.0, duration, bends)]
    return detect_bends_and_slides(events, notes, config)[0]


def test_two_semitone_rise_is_full_bend():
    out = _single(_bend_curve(2 * BINS))
    assert out.technique is not None
    assert out.technique.kind == TECHNIQUE_BEND
    assert out.technique.bend_semitones == 2.0
    assert out.technique.bend_curve[0] == 0.0
    assert out.technique.bend_curve[-1] == 2.0


def test_one_semitone_rise_is_half_step_bend():
    out = _single(_bend_curve(1 * BINS))
    assert out.technique is not None
    assert out.technique.kind == TECHNIQUE_BEND
    assert out.technique.bend_semitones == 1.0


def test_bend_with_release_keeps_curve_shape():
    out = _single(_bend_curve(2 * BINS, release=True))
    assert out.technique is not None
    assert out.technique.bend_semitones == 2.0
    curve = out.technique.bend_curve
    assert curve[0] == 0.0 and curve[-1] == 0.0 and max(curve) == 2.0


def test_vibrato_is_not_a_bend():
    vibrato = _vibrato()
    assert max(vibrato) == 1 and min(vibrato) == -1
    assert _single(vibrato).technique is None


def test_random_pitch_noise_is_not_a_bend():
    rng = random.Random(1234)
    noise = [rng.randint(-3, 3) for _ in range(200)]
    assert _single(noise).technique is None


def test_short_blip_is_not_a_bend():
    blip = [0] * 20 + [6] * 3 + [0] * 20
    assert _single(blip).technique is None


def test_no_bend_data_means_no_technique():
    assert _single(None).technique is None


def _slide_pair(second_string: int) -> tuple[list[TabNote], list[Note]]:
    """Fret 5 -> 7 with a continuous glide at the end of the first note."""
    hold = [0] * 30
    glide = [1, 2, 3, 4, 5, 6, 6, 6]
    first_end = (len(hold) + len(glide)) / BASIC_PITCH_FPS
    second_end = first_end + 0.4
    second_fret = 7 if second_string == 3 else 3  # D4 (MIDI 62) either way
    events = [
        _event(3, 5, 0.0, first_end),
        _event(second_string, second_fret, first_end, second_end),
    ]
    notes = [
        _note(60, 0.0, first_end, hold + glide),
        _note(62, first_end, second_end, [0] * 34),
    ]
    return events, notes


def test_glide_between_same_string_notes_is_slide_up():
    events, notes = _slide_pair(second_string=3)
    out = detect_bends_and_slides(events, notes)
    tech = out[0].technique
    assert tech is not None
    assert tech.kind == TECHNIQUE_SLIDE
    assert tech.slide_direction == SLIDE_UP
    assert tech.target_fret == 7
    assert out[1].technique is None


def test_glide_across_strings_is_not_slide():
    events, notes = _slide_pair(second_string=2)
    out = detect_bends_and_slides(events, notes)
    assert all(e.technique is None or e.technique.kind != TECHNIQUE_SLIDE for e in out)


def test_slide_down_detected_from_head_of_second_note():
    events = [_event(3, 7, 0.0, 0.4), _event(3, 5, 0.4, 0.8)]
    notes = [
        _note(62, 0.0, 0.4, [0] * 34),
        _note(60, 0.4, 0.8, [6, 5, 3, 1, 0, 0] + [0] * 28),
    ]
    tech = detect_bends_and_slides(events, notes)[0].technique
    assert tech is not None
    assert tech.kind == TECHNIQUE_SLIDE
    assert tech.slide_direction == SLIDE_DOWN
    assert tech.target_fret == 5


def test_same_string_without_glide_is_not_slide():
    events = [_event(3, 5, 0.0, 0.4), _event(3, 7, 0.4, 0.8)]
    notes = [_note(60, 0.0, 0.4, [0] * 34), _note(62, 0.4, 0.8, [0] * 34)]
    out = detect_bends_and_slides(events, notes)
    assert [e.technique for e in out] == [None, None]


def test_existing_technique_is_kept_and_inputs_untouched():
    hammer = Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)
    events, notes = _slide_pair(second_string=3)
    payload = {**events[0].to_dict(), "technique": hammer.to_dict()}
    events[0] = TabNote.from_dict(payload)
    before = [e.to_dict() for e in events]
    out = detect_bends_and_slides(events, notes)
    assert out[0].technique == hammer
    assert [e.to_dict() for e in events] == before
    assert out[0] is not events[0]


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        detect_bends_and_slides([_event(1, 0, 0.0, 1.0)], [])


# Controls: the same inputs DO become bends once the guards are removed,
# so the negative tests above depend on smoothing, duration and amplitude.
NAIVE = BendConfig(smoothing_frames=1, min_bend_duration_s=0.0)


def test_control_noise_is_a_bend_without_smoothing_and_duration():
    rng = random.Random(1234)
    noise = [rng.randint(-3, 3) for _ in range(200)]
    tech = _single(noise, NAIVE).technique
    assert tech is not None and tech.kind == TECHNIQUE_BEND


def test_control_vibrato_is_a_bend_with_low_amplitude_threshold():
    vibrato = _vibrato()
    low = BendConfig(
        smoothing_frames=1, min_bend_duration_s=0.0, min_bend_semitones=0.3
    )
    tech = _single(vibrato, low).technique
    assert tech is not None and tech.kind == TECHNIQUE_BEND
