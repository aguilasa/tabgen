"""MusicXML export: files re-read by music21 keep measures, pitches and key."""

from fractions import Fraction

import pytest
from music21 import converter, harmony, key, stream, tempo

from tabgen.core.export.musicxml import MusicXmlExportError, export_musicxml
from tabgen.core.models import (
    BASS_STANDARD_TUNING,
    MeasureChord,
    TabNote,
    TabScore,
)


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


def _pitch_seq(part):
    """Sorted MIDI pitches of each note/chord, in onset order, ties merged."""
    out = []
    for element in part.flatten().notes:
        if isinstance(element, harmony.ChordSymbol):
            continue  # harmony annotation, not a sounding note
        if element.tie is not None and element.tie.type != "start":
            continue  # continuation of a tied note
        out.append(sorted(p.midi for p in element.pitches))
    return out


def test_roundtrip_measures_pitches_key_and_tempo(tmp_path):
    score = TabScore(
        instrument="guitar",
        tempo_bpm=132.0,
        key="E minor",
        capo_fret=2,
        time_signature=[4, 4],
        events=[
            _note(6, 0, measure=1, beat=1, duration=4),  # 40 + 2
            _note(5, 2, measure=1, beat=2, duration=4),  # 47 + 2
            _note(4, 2, measure=1, beat=3, duration=2),  # 52 + 2
            _note(3, 0, measure=1, beat=3, subdivision=2, duration=2),  # 55 + 2
            _note(2, 0, measure=2, beat=1, duration=16),  # 59 + 2
            _note(1, 0, measure=2, beat=1, duration=16),  # 64 + 2
        ],
        chords=[MeasureChord(measure=1, label="E:min"), MeasureChord(2, "N")],
    )
    path = export_musicxml(score, tmp_path / "out.musicxml")

    parsed = converter.parse(str(path))
    part = parsed.parts[0]
    assert len(part.getElementsByClass(stream.Measure)) == 2
    assert _pitch_seq(part) == [[42], [49], [54], [57], [61, 66]]

    signature = part.recurse().getElementsByClass(key.KeySignature).first()
    assert signature.sharps == 1  # E minor
    mark = parsed.recurse().getElementsByClass(tempo.MetronomeMark).first()
    assert mark is not None and mark.number == 132

    symbols = list(part.recurse().getElementsByClass(harmony.ChordSymbol))
    assert len(symbols) == 1  # "N" in measure 2 is not annotated
    assert symbols[0].root().name == "E"
    assert symbols[0].chordKind == "minor"


def test_triplets_and_measure_crossing_tie(tmp_path):
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
    path = export_musicxml(
        [score], tmp_path / "out.musicxml", beat_grids=[[3, 3, 3, 4]]
    )

    parsed = converter.parse(str(path))
    part = parsed.parts[0]
    assert len(part.getElementsByClass(stream.Measure)) == 2
    assert _pitch_seq(part) == [[64], [66], [67], [52]]

    notes = [n for n in part.flatten().notes if n.tie is None or n.tie.type == "start"]
    assert [n.duration.quarterLength for n in notes[:3]] == [Fraction(1, 3)] * 3
    # The tied half note continues into measure 2.
    stops = [
        n
        for n in part.flatten().notes
        if n.tie is not None and n.tie.type == "stop"
    ]
    assert len(stops) == 1
    assert stops[0].pitch.midi == 52
    assert stops[0].measureNumber == 2


def test_two_parts_and_full_measure_lengths(tmp_path):
    guitar = TabScore(
        instrument="guitar",
        tempo_bpm=90.0,
        time_signature=[4, 4],
        events=[_note(1, 0, measure=1, beat=2, duration=4)],
    )
    bass = TabScore(
        instrument="bass",
        tuning_midi=list(BASS_STANDARD_TUNING),
        tempo_bpm=90.0,
        time_signature=[4, 4],
        events=[_note(4, 5, measure=2, beat=1, duration=16)],
    )
    path = export_musicxml([guitar, bass], tmp_path / "duo.musicxml")

    parsed = converter.parse(str(path))
    assert len(parsed.parts) == 2
    assert [p.partName for p in parsed.parts] == ["guitar", "bass"]
    for part in parsed.parts:
        measures = list(part.getElementsByClass(stream.Measure))
        assert len(measures) == 2
        for measure in measures:  # rests fill gaps up to the signature
            assert measure.duration.quarterLength == 4


def test_rejects_mismatched_time_signatures_and_bad_strings(tmp_path):
    a = TabScore(time_signature=[4, 4])
    b = TabScore(time_signature=[3, 4])
    with pytest.raises(MusicXmlExportError, match="time signature"):
        export_musicxml([a, b], tmp_path / "bad.musicxml")

    out_of_range = TabScore(events=[_note(7, 0, measure=1, beat=1)])
    with pytest.raises(MusicXmlExportError, match="string 7"):
        export_musicxml(out_of_range, tmp_path / "bad.musicxml")
