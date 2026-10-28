"""GP5 export: written .gp5 files re-read with the same notes and grid."""

import guitarpro
import pytest

from tabgen.core.export.gp5 import Gp5ExportError, export_gp5
from tabgen.core.models import (
    BASS_STANDARD_TUNING,
    GUITAR_STANDARD_TUNING,
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

QUARTER = guitarpro.Duration.quarterTime  # 960 ticks


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


def _read_notes(track, beat_ticks):
    """Walk a track's beats: (string, fret, measure, beat) of normal notes."""
    found = []
    for measure in track.measures:
        cursor = 0
        for beat in measure.voices[0].beats:
            for note in beat.notes:
                if note.type == guitarpro.NoteType.normal:
                    found.append(
                        (
                            note.string,
                            note.value,
                            measure.header.number,
                            cursor // beat_ticks + 1,
                        )
                    )
            cursor += beat.duration.time
    return found


def _assert_measures_sum(song):
    """Every measure's voice sums exactly to the time signature length."""
    for track in song.tracks:
        for measure in track.measures:
            total = sum(b.duration.time for b in measure.voices[0].beats)
            assert total == measure.length, (
                f"track {track.name} measure {measure.header.number}: "
                f"{total} != {measure.length}"
            )


def test_roundtrip_preserves_notes_tuning_and_bpm(tmp_path):
    score = TabScore(
        instrument="guitar",
        tempo_bpm=132.0,
        key="A minor",
        capo_fret=2,
        time_signature=[4, 4],
        events=[
            _note(6, 0, measure=1, beat=1, duration=4),
            _note(5, 2, measure=1, beat=2, duration=2),
            _note(1, 3, measure=1, beat=3, subdivision=2, duration=2),
            _note(3, 5, measure=2, beat=1, duration=16),
        ],
    )
    path = export_gp5(score, tmp_path / "out.gp5")

    song = guitarpro.parse(str(path))
    assert song.tempo == 132
    assert len(song.tracks) == 1
    track = song.tracks[0]
    assert track.offset == 2  # capo
    assert [s.value for s in track.strings] == list(
        reversed(GUITAR_STANDARD_TUNING)
    )
    assert [s.number for s in track.strings] == [1, 2, 3, 4, 5, 6]
    assert _read_notes(track, QUARTER) == [
        (6, 0, 1, 1),
        (5, 2, 1, 2),
        (1, 3, 1, 3),
        (3, 5, 2, 1),
    ]
    _assert_measures_sum(song)


def test_measures_sum_with_triplet_and_tie_across_measures(tmp_path):
    score = TabScore(
        instrument="guitar",
        tempo_bpm=100.0,
        time_signature=[4, 4],
        events=[
            # Three triplet eighths filling measure 1, beat 1 (3-grid).
            _note(2, 5, measure=1, beat=1, subdivision=0, duration=1),
            _note(2, 7, measure=1, beat=1, subdivision=1, duration=1),
            _note(2, 8, measure=1, beat=1, subdivision=2, duration=1),
            # Half note on beat 4: one beat remains, so it ties into m. 2.
            _note(4, 2, measure=1, beat=4, subdivision=0, duration=8),
        ],
    )
    beat_grids = [[3, 3, 3, 4]]
    path = export_gp5([score], tmp_path / "out.gp5", beat_grids=beat_grids)

    song = guitarpro.parse(str(path))
    _assert_measures_sum(song)
    track = song.tracks[0]

    triplets = [
        b
        for b in track.measures[0].voices[0].beats
        if b.duration.tuplet == guitarpro.Tuplet(3, 2)
    ]
    assert len(triplets) == 3
    assert [b.notes[0].value for b in triplets] == [5, 7, 8]

    measure2 = track.measures[1].voices[0].beats
    tied = [n for b in measure2 for n in b.notes]
    assert len(tied) == 1
    assert tied[0].type == guitarpro.NoteType.tie
    assert (tied[0].string, tied[0].value) == (4, 2)
    # The tie continuation sits at the start of measure 2, one beat long.
    assert measure2[0].notes and measure2[0].duration.time == QUARTER


def test_two_tracks_rests_and_chord_labels(tmp_path):
    guitar = TabScore(
        instrument="guitar",
        tempo_bpm=90.0,
        time_signature=[4, 4],
        events=[_note(1, 0, measure=1, beat=2, duration=4)],
        chords=[MeasureChord(measure=1, label="A:min"), MeasureChord(2, "N")],
    )
    bass = TabScore(
        instrument="bass",
        tuning_midi=list(BASS_STANDARD_TUNING),
        tempo_bpm=90.0,
        time_signature=[4, 4],
        events=[_note(4, 5, measure=2, beat=1, duration=16)],
    )
    path = export_gp5([guitar, bass], tmp_path / "duo.gp5")

    song = guitarpro.parse(str(path))
    assert [t.name for t in song.tracks] == ["guitar", "bass"]
    assert [s.value for s in song.tracks[1].strings] == list(
        reversed(BASS_STANDARD_TUNING)
    )
    _assert_measures_sum(song)
    assert _read_notes(song.tracks[0], QUARTER) == [(1, 0, 1, 2)]
    assert _read_notes(song.tracks[1], QUARTER) == [(4, 5, 2, 1)]

    beats_m1 = song.tracks[0].measures[0].voices[0].beats
    assert beats_m1[0].status == guitarpro.BeatStatus.rest  # leading rest
    assert beats_m1[0].effect.chord is not None
    assert beats_m1[0].effect.chord.name == "A:min"
    # "N" (no chord) in measure 2 is not annotated.
    for beat in song.tracks[0].measures[1].voices[0].beats:
        assert beat.effect.chord is None


def test_rejects_mismatched_time_signatures_and_bad_strings(tmp_path):
    a = TabScore(time_signature=[4, 4])
    b = TabScore(time_signature=[3, 4])
    with pytest.raises(Gp5ExportError, match="time signature"):
        export_gp5([a, b], tmp_path / "bad.gp5")

    out_of_range = TabScore(events=[_note(7, 0, measure=1, beat=1)])
    with pytest.raises(Gp5ExportError, match="string 7"):
        export_gp5(out_of_range, tmp_path / "bad.gp5")


def _technique_score():
    """One measure with the four techniques, each on its origin note.

    Beat 1: bend 7 (string 3, whole step, curve rising then holding).
    Beat 2: slide 5 -> 7 on string 2 (8ths). Beat 3: hammer 5 -> 7 on
    string 1. Beat 4: pull 7 -> 5 on string 1 (also slide down 9 -> 7 on
    string 4 of a two-note beat, to pin per-note placement in a chord).
    """
    bend = Technique(
        kind=TECHNIQUE_BEND, bend_semitones=2.0, bend_curve=[0.0, 1.0, 2.0, 2.0, 2.0]
    )
    slide = Technique(kind=TECHNIQUE_SLIDE, slide_direction=SLIDE_UP, target_fret=7)
    down = Technique(kind=TECHNIQUE_SLIDE, slide_direction=SLIDE_DOWN, target_fret=7)
    hammer = Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)
    pull = Technique(kind=TECHNIQUE_PULL_OFF, target_fret=5)
    events = [
        _note(3, 7, 1, 1, duration=4),
        _note(2, 5, 1, 2, 0, duration=2),
        _note(2, 7, 1, 2, 2, duration=2),
        _note(1, 5, 1, 3, 0, duration=2),
        _note(1, 7, 1, 3, 2, duration=2),
        _note(1, 7, 1, 4, 0, duration=2),
        _note(4, 9, 1, 4, 0, duration=2),
        _note(1, 5, 1, 4, 2, duration=2),
        _note(4, 7, 1, 4, 2, duration=2),
    ]
    for index, technique in ((0, bend), (1, slide), (3, hammer), (5, pull), (6, down)):
        events[index].technique = technique
    return TabScore(instrument="guitar", time_signature=[4, 4], events=events)


def _effects(path):
    """(string, fret) -> (bend points, slides, hammer) of every re-read note."""
    song = guitarpro.parse(str(path))
    out = []
    for beat in song.tracks[0].measures[0].voices[0].beats:
        for note in beat.notes:
            bend = note.effect.bend
            out.append(
                (
                    note.string,
                    note.value,
                    [(p.position, p.value) for p in bend.points] if bend else None,
                    list(note.effect.slides),
                    note.effect.hammer,
                )
            )
    return out


def test_techniques_roundtrip_as_note_effects(tmp_path):
    path = export_gp5(_technique_score(), tmp_path / "fx.gp5")
    shift = guitarpro.SlideType.shiftSlideTo
    # Bend points are in quarter tones: a whole step peaks at 4.
    assert _effects(path) == [
        (3, 7, [(0, 0), (3, 2), (6, 4), (9, 4), (12, 4)], [], False),
        (2, 5, None, [shift], False),
        (2, 7, None, [], False),
        (1, 5, None, [], True),
        (1, 7, None, [], False),
        (1, 7, None, [], True),
        (4, 9, None, [shift], False),
        (1, 5, None, [], False),
        (4, 7, None, [], False),
    ]
    song = guitarpro.parse(str(path))
    bend = song.tracks[0].measures[0].voices[0].beats[0].notes[0].effect.bend
    assert bend.type == guitarpro.BendType.bend and bend.value == 100


def test_plain_bend_without_curve_rises_and_holds(tmp_path):
    note = _note(3, 7, 1, 1)
    note.technique = Technique(kind=TECHNIQUE_BEND, bend_semitones=1.0)
    path = export_gp5(TabScore(events=[note]), tmp_path / "b.gp5")
    assert _effects(path)[0][2] == [(0, 0), (6, 2), (12, 2)]


def test_link_effect_goes_on_the_last_tied_chunk(tmp_path):
    origin = _note(2, 5, 1, 4, duration=8)  # crosses into measure 2
    origin.technique = Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)
    bend = _note(3, 7, 1, 4, duration=8)
    bend.technique = Technique(kind=TECHNIQUE_BEND, bend_semitones=1.0)
    path = export_gp5(
        TabScore(events=[origin, bend, _note(2, 7, 2, 2)]), tmp_path / "t.gp5"
    )
    song = guitarpro.parse(str(path))
    notes = [
        (m.header.number, n.string, n.type, n.effect.hammer, n.effect.bend is not None)
        for m in song.tracks[0].measures
        for b in m.voices[0].beats
        for n in b.notes
    ]
    normal, tie = guitarpro.NoteType.normal, guitarpro.NoteType.tie
    assert (1, 2, normal, False, False) in notes
    assert (2, 2, tie, True, False) in notes
    assert (1, 3, normal, False, True) in notes
    assert (2, 3, tie, False, False) in notes


def test_five_string_bass_track_keeps_five_strings_and_tuning(tmp_path):
    from tabgen.core.models import BASS_FIVE_STRING_TUNING

    bass = TabScore(
        instrument="bass",
        tuning_midi=list(BASS_FIVE_STRING_TUNING),
        tempo_bpm=100.0,
        events=[_note(5, 0, measure=1, beat=1), _note(4, 3, measure=1, beat=2)],
    )
    out = export_gp5(bass, tmp_path / "bass5.gp5")
    song = guitarpro.parse(str(out))
    (track,) = song.tracks
    assert len(track.strings) == 5
    # String 1 = highest: G2 D2 A1 E1 B0.
    assert [s.value for s in track.strings] == [43, 38, 33, 28, 23]
    assert _read_notes(track, QUARTER)[:2] == [(5, 0, 1, 1), (4, 3, 1, 2)]
    assert track.channel.instrument == 33


@pytest.mark.parametrize(
    ("instrument_type", "program"),
    [("nylon", 24), ("steel", 25), ("electric", 27), ("", 27)],
)
def test_guitar_type_sets_the_track_program(tmp_path, instrument_type, program):
    score = TabScore(
        instrument="guitar",
        instrument_type=instrument_type,
        events=[_note(1, 0, measure=1, beat=1)],
    )
    out = export_gp5(score, tmp_path / "g.gp5")
    assert guitarpro.parse(str(out)).tracks[0].channel.instrument == program
