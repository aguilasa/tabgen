"""MusicXML export: files re-read by music21 keep measures, pitches and key."""

from fractions import Fraction

import pytest
from music21 import converter, harmony, key, stream, tempo

from tabgen.core.export.musicxml import MusicXmlExportError, export_musicxml
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


def test_techniques_reread_as_technical_notations(tmp_path):
    """Bend, slide, hammer-on and pull-off survive a music21 round-trip on
    the right notes (spanners link the origin to the next note)."""
    events = [
        _note(3, 7, 1, 1, duration=4),  # bend: D4 (62) -> whole step
        _note(2, 5, 1, 2, 0, duration=2),  # slide up 64 -> 66
        _note(2, 7, 1, 2, 2, duration=2),
        _note(1, 5, 1, 3, 0, duration=2),  # hammer 69 -> 71
        _note(1, 7, 1, 3, 2, duration=2),  # pull 71 -> 69
        _note(1, 5, 1, 4, 0, duration=4),
    ]
    events[0].technique = Technique(
        kind=TECHNIQUE_BEND, bend_semitones=2.0, bend_curve=[0.0, 2.0, 2.0, 2.0, 2.0]
    )
    events[1].technique = Technique(
        kind=TECHNIQUE_SLIDE, slide_direction=SLIDE_UP, target_fret=7
    )
    events[3].technique = Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)
    events[4].technique = Technique(kind=TECHNIQUE_PULL_OFF, target_fret=5)
    path = export_musicxml(
        TabScore(time_signature=[4, 4], events=events), tmp_path / "fx.musicxml"
    )
    xml = path.read_text(encoding="utf-8")
    assert "<bend-alter>2</bend-alter>" in xml
    assert 'line-type="solid"' in xml

    notes = list(converter.parse(str(path)).recurse().notes)
    assert [n.pitch.midi for n in notes] == [62, 64, 66, 69, 71, 69]

    def fx(note):
        bends = [
            a.bendAlter.semitones
            for a in note.articulations
            if type(a).__name__ == "FretBend"
        ]
        spans = sorted(
            (type(s).__name__, "start" if s.isFirst(note) else "stop")
            for s in note.getSpannerSites()
        )
        return bends, spans

    assert [fx(n) for n in notes] == [
        ([2.0], []),
        ([], [("Glissando", "start")]),
        ([], [("Glissando", "stop")]),
        ([], [("HammerOn", "start")]),
        ([], [("HammerOn", "stop"), ("PullOff", "start")]),
        ([], [("PullOff", "stop")]),
    ]
    glissando = next(s for s in notes[1].getSpannerSites())
    assert glissando.slideType == "continuous"


def test_link_technique_without_next_note_is_dropped(tmp_path):
    last = _note(1, 5, 1, 1)
    last.technique = Technique(kind=TECHNIQUE_HAMMER_ON, target_fret=7)
    other = _note(2, 5, 1, 2)
    other.technique = Technique(
        kind=TECHNIQUE_SLIDE, slide_direction=SLIDE_DOWN, target_fret=3
    )
    path = export_musicxml(TabScore(events=[last, other]), tmp_path / "x.musicxml")
    xml = path.read_text(encoding="utf-8")
    assert "hammer-on" not in xml and "<slide" not in xml
