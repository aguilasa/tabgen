"""GP5 export: written .gp5 files re-read with the same notes and grid."""

import guitarpro
import pytest

from tabgen.core.export.gp5 import Gp5ExportError, export_gp5
from tabgen.core.models import (
    BASS_STANDARD_TUNING,
    GUITAR_STANDARD_TUNING,
    MeasureChord,
    TabNote,
    TabScore,
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
