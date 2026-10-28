"""Fretting DP: known scales and chords land on playable (string, fret)."""

from tabgen.core.fretting import (
    FrettingConfig,
    assign_frets,
    bass_config,
    guitar_config,
)
from tabgen.core.models import ChordSegment, Note, NoteEvents

# Written-pitch standard tuning (guitar is a transposing instrument: written
# one octave above sounding). The task's pentatonic pitch list (57..81) is in
# written pitch; with the sounding-pitch tuning those notes sit above fret 8.
GUITAR_WRITTEN_TUNING = [52, 57, 62, 67, 71, 76]


def _melody(pitches: list[int], step_s: float = 0.5) -> list[Note]:
    return [
        Note(pitch_midi=p, start_s=i * step_s, end_s=i * step_s + 0.4)
        for i, p in enumerate(pitches)
    ]


def _chord(pitches: list[int], start_s: float = 0.0) -> list[Note]:
    return [
        Note(pitch_midi=p, start_s=start_s, end_s=start_s + 1.0)
        for p in pitches
    ]


def test_a_minor_pentatonic_stays_in_fifth_position_box():
    pitches = [57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81]
    config = FrettingConfig(tuning_midi=GUITAR_WRITTEN_TUNING)
    result = assign_frets(NoteEvents(notes=_melody(pitches)), config)

    assert not result.unassigned
    assert len(result.assignments) == len(pitches)
    frets = [fn.fret for fn in result.assignments]
    assert all(5 <= f <= 8 for f in frets), frets
    jumps = [abs(a - b) for a, b in zip(frets, frets[1:])]
    assert all(j <= 4 for j in jumps), jumps


def test_open_c_major_shape_with_chord_prior():
    pitches = [48, 52, 55, 60, 64]
    chords = [ChordSegment(start_s=0.0, end_s=2.0, label="C:maj")]
    result = assign_frets(_chord(pitches), guitar_config(), chords=chords)

    assert not result.unassigned
    strings = [fn.string for fn in result.assignments]
    assert len(set(strings)) == len(strings)  # one string per note
    placed = {fn.note.pitch_midi: (fn.string, fn.fret) for fn in result.assignments}
    # Open C shape, guitarist numbering (string 6 = low E, string 1 = high e).
    assert placed == {48: (5, 3), 52: (4, 2), 55: (3, 0), 60: (2, 1), 64: (1, 0)}


def test_drop_d_low_string_and_out_of_range_report():
    config = FrettingConfig(tuning_midi=[38, 45, 50, 55, 59, 64])
    notes = _melody([38, 30])  # 30 is below the lowest open string
    result = assign_frets(notes, config)

    assert len(result.assignments) == 1
    low = result.assignments[0]
    assert (low.note.pitch_midi, low.string, low.fret) == (38, 6, 0)
    assert len(result.unassigned) == 1
    assert result.unassigned[0].note.pitch_midi == 30
    assert "not playable" in result.unassigned[0].reason


def test_bass_assigns_full_e_minor_line():
    pitches = [28, 30, 31, 33, 35, 36, 38, 40, 43]
    config = bass_config()
    result = assign_frets(_melody(pitches), config)

    assert not result.unassigned
    assert len(result.assignments) == len(pitches)
    for fn in result.assignments:
        assert 1 <= fn.string <= 4
        assert 0 <= fn.fret <= config.max_fret
        sounding = config.tuning_midi[len(config.tuning_midi) - fn.string]
        assert sounding + fn.fret == fn.note.pitch_midi


def test_simultaneous_notes_never_share_a_string():
    # Dense cluster: 6 notes at once on a 6-string guitar.
    result = assign_frets(_chord([40, 45, 50, 55, 59, 64]), guitar_config())
    assert not result.unassigned
    strings = [fn.string for fn in result.assignments]
    assert sorted(strings) == [1, 2, 3, 4, 5, 6]


def test_more_notes_than_strings_reports_leftover():
    result = assign_frets(_chord([40, 45, 50, 55, 59, 64, 69]), guitar_config())
    assert len(result.assignments) == 6
    assert len(result.unassigned) == 1
    assert "no free string" in result.unassigned[0].reason


def test_capo_shifts_candidates():
    config = guitar_config(capo_fret=2)
    result = assign_frets(_melody([42]), config)  # low E + capo 2 = F#2
    assert len(result.assignments) == 1
    assert (result.assignments[0].string, result.assignments[0].fret) == (6, 0)


def test_five_string_bass_places_low_b_open_on_string_five():
    from tabgen.core.fretting.dp import five_string_bass_config

    line = _melody([23, 28, 33])  # B0 E1 A1
    result = assign_frets(line, five_string_bass_config())
    assert not result.unassigned
    low_b = result.assignments[0]
    assert (low_b.note.pitch_midi, low_b.string, low_b.fret) == (23, 5, 0)

    four = assign_frets(line, bass_config())
    assert [u.note.pitch_midi for u in four.unassigned] == [23]
    assert "not playable" in four.unassigned[0].reason
    assert all(fn.note.pitch_midi != 23 for fn in four.assignments)


def test_guitar_type_sets_max_fret():
    from tabgen.core.fretting.dp import GUITAR_MAX_FRETS

    assert GUITAR_MAX_FRETS == {"electric": 24, "steel": 20, "nylon": 19}
    assert guitar_config().max_fret == 24  # default: electric
    assert guitar_config("nylon").max_fret == 19
    assert guitar_config("steel").max_fret == 20
    # E6 (88) needs fret 24 on the high e: playable on electric only.
    assert not assign_frets(_melody([88]), guitar_config("electric")).unassigned
    nylon = assign_frets(_melody([88]), guitar_config("nylon"))
    assert [u.note.pitch_midi for u in nylon.unassigned] == [88]


def test_sparse_line_is_not_pushed_above_the_twelfth_fret():
    # Regression (REF-TASK-04 finding): with the string-index preference
    # alone this D4 A4 B4 E4 line landed at frets 21-24 on the low strings.
    notes = [
        Note(62, 0.5, 0.95),
        Note(69, 1.0, 1.25),
        Note(71, 1.25, 1.45),
        Note(64, 2.0, 2.45),
    ]
    chords = [ChordSegment(start_s=0.0, end_s=3.0, label="E:min")]
    for prior in (None, chords):
        result = assign_frets(notes, guitar_config(), chords=prior)
        assert not result.unassigned
        frets = [fn.fret for fn in result.assignments]
        assert max(frets) <= 12, frets
