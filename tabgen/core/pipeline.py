"""Pipeline primitives and stage orchestration.

Holds the progress-reporting contract shared by every stage and the two
orchestrators: :func:`run_transcription`, which chains separation →
per-instrument transcription → MIDI export, and :func:`run_analysis`,
which chains separation → beats → harmony into one
:class:`~tabgen.core.models.AnalysisResult`. Heavy stage modules are
imported lazily so importing this module stays cheap; the stage
functions are injectable for tests.

This module is pure core: no print/typer/rich.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional, Protocol, Sequence

from tabgen.core.cache import StageCache
from tabgen.core.models import (
    DEFAULT_GUITAR_TYPE,
    TAB_FORMAT_VERSION,
    AnalysisResult,
    ChordSegment,
    MeasureChord,
    Note,
    NoteEvents,
    TabNote,
    TabScore,
)

# Called as on_progress(stage, pct) with pct in [0.0, 100.0].
ProgressCallback = Callable[[str, float], None]


def null_progress(stage: str, pct: float) -> None:
    """A ProgressCallback that ignores every update."""


class PipelineError(RuntimeError):
    """Raised when the pipeline cannot orchestrate its stages."""


class _SeparateFn(Protocol):
    def __call__(
        self,
        input_path: Path,
        device: Optional[str] = None,
        on_progress: ProgressCallback = null_progress,
    ): ...


class _TranscribeFn(Protocol):
    def __call__(
        self,
        input_path: Path,
        instrument: str = "guitar",
        on_progress: ProgressCallback = null_progress,
    ): ...


class _ExportFn(Protocol):
    def __call__(
        self, note_events, output_path: Path, bends=None, **kwargs
    ) -> Path: ...


class _BeatsFn(Protocol):
    def __call__(
        self,
        audio_path: Path,
        on_progress: ProgressCallback = null_progress,
    ): ...


class _HarmonyFn(Protocol):
    def __call__(
        self,
        stems: Mapping[str, str],
        on_progress: ProgressCallback = null_progress,
    ): ...


@dataclass
class InstrumentSummary:
    """Per-instrument outcome of :func:`run_transcription`."""

    instrument: str
    note_count: int
    midi_path: str
    cache_hit: bool  # transcription-stage cache hit for this instrument


@dataclass
class TranscriptionSummary:
    """Overall outcome of :func:`run_transcription`."""

    input_path: str
    separation_cache_hit: bool
    instruments: list[InstrumentSummary] = field(default_factory=list)


# Guitar transcribers (stage 4). The bass always uses Basic Pitch.
TRANSCRIBER_BASIC_PITCH = "basic-pitch"
TRANSCRIBER_RILEY = "riley"
TRANSCRIBERS = (TRANSCRIBER_BASIC_PITCH, TRANSCRIBER_RILEY)
# Riley became the default after beating Basic Pitch in both note-F1 and
# tab-F1 on Demucs stems of the mixed EGDB subset (REF-TASK-09, see
# docs/avaliacao/modelo-guitarra.md).
DEFAULT_TRANSCRIBER = TRANSCRIBER_RILEY


def _check_transcriber(transcriber: str) -> None:
    """Raise PipelineError unless ``transcriber`` is one of TRANSCRIBERS."""
    if transcriber not in TRANSCRIBERS:
        raise PipelineError(
            f"unknown transcriber {transcriber!r}; choose one of "
            f"{', '.join(TRANSCRIBERS)}"
        )


def default_transcribe_fn(
    transcriber: str = DEFAULT_TRANSCRIBER, device: str | None = None
) -> _TranscribeFn:
    """The real transcription stage for ``transcriber``.

    ``basic-pitch`` is Basic Pitch for every instrument. ``riley`` routes
    the guitar to the hybrid Riley transcription (Riley notes, Basic Pitch
    bends; :mod:`tabgen.core.transcription.riley`) and keeps Basic Pitch
    for the bass.
    """
    _check_transcriber(transcriber)
    from tabgen.core.transcription.basic_pitch import transcribe as bp_transcribe

    if transcriber == TRANSCRIBER_BASIC_PITCH:
        return bp_transcribe

    def transcribe(
        input_path: Path,
        instrument: str = "guitar",
        on_progress: ProgressCallback = null_progress,
    ):
        if instrument != "guitar":
            return bp_transcribe(
                input_path, instrument=instrument, on_progress=on_progress
            )
        from tabgen.core.transcription.riley import transcribe as riley_transcribe

        return riley_transcribe(
            input_path, instrument=instrument, on_progress=on_progress,
            device=device,
        )

    return transcribe


def transcriber_tag(transcriber: str, instruments: Sequence[str]) -> str:
    """Cache-key tag of the guitar transcriber (empty for Basic Pitch).

    With ``riley`` and a guitar part it is ``+riley-<weights sha256
    prefix>-<digest of the hybrid transcription version>`` (the digest pins
    the Basic Pitch bend source and the matching tolerance). It is kept
    short: the cache file name already sits near the 255-byte limit.
    """
    _check_transcriber(transcriber)
    if transcriber == TRANSCRIBER_BASIC_PITCH or "guitar" not in instruments:
        return ""
    import hashlib

    from tabgen.core.transcription.riley import (
        WEIGHTS_SHA256,
        transcription_version,
    )

    digest = hashlib.sha256(
        transcription_version("guitar").encode("utf-8")
    ).hexdigest()[:6]
    return f"+riley-{WEIGHTS_SHA256[:8]}-{digest}"


def _scoped_progress(
    on_progress: ProgressCallback, stage_name: str
) -> ProgressCallback:
    """Forward pct updates under a fixed stage name (e.g. per instrument)."""

    def callback(stage: str, pct: float) -> None:
        on_progress(stage_name, pct)

    return callback


def run_transcription(
    input_path: str | Path,
    instruments: Sequence[str] = ("guitar", "bass"),
    device: str | None = None,
    output_dir: str | Path | None = None,
    on_progress: ProgressCallback = null_progress,
    separate_fn: _SeparateFn | None = None,
    transcribe_fn: _TranscribeFn | None = None,
    export_fn: _ExportFn | None = None,
    guitar_type: str | None = None,
    transcriber: str = DEFAULT_TRANSCRIBER,
) -> TranscriptionSummary:
    """Separate the input, transcribe each instrument's stem, export MIDI.

    One ``.mid`` file is written per instrument, named
    ``<input-stem>.<instrument>.mid`` and placed next to the input (or in
    ``output_dir`` when given). Progress is reported per stage: the
    ``separation`` events come straight from the separation stage, then
    ``transcription:<instrument>`` and ``export:<instrument>`` follow for
    each instrument, every stage reaching 100.0.

    ``separate_fn`` / ``transcribe_fn`` / ``export_fn`` default to the real
    stages and exist for dependency injection in tests.

    ``guitar_type`` (one of ``models.GUITAR_TYPES``) picks the General MIDI
    program of the guitar file (e.g. ``"nylon"`` = 24); ``None`` keeps the
    exporter's default (electric guitar).

    ``transcriber`` (one of :data:`TRANSCRIBERS`) picks the guitar's
    transcription when ``transcribe_fn`` is not injected (see
    :func:`default_transcribe_fn`); the bass always uses Basic Pitch.
    """
    input_path = Path(input_path)
    if not instruments:
        raise PipelineError("no instruments requested")
    _check_guitar_type(guitar_type)
    _check_transcriber(transcriber)

    if separate_fn is None:
        from tabgen.core.separation.demucs import separate as separate_fn
    if transcribe_fn is None:
        transcribe_fn = default_transcribe_fn(transcriber, device)
    if export_fn is None:
        from tabgen.core.export.midi import export_midi as export_fn

    target_dir = Path(output_dir) if output_dir is not None else input_path.parent

    separation, separation_hit = separate_fn(
        input_path, device=device, on_progress=on_progress
    )

    missing = [name for name in instruments if name not in separation.stems]
    if missing:
        available = ", ".join(sorted(separation.stems)) or "none"
        raise PipelineError(
            f"no stem for instrument(s) {', '.join(missing)}; "
            f"available stems: {available}"
        )

    summary = TranscriptionSummary(
        input_path=str(input_path), separation_cache_hit=separation_hit
    )
    for instrument in instruments:
        stem_path = Path(separation.stems[instrument])
        result, transcription_hit = transcribe_fn(
            stem_path,
            instrument=instrument,
            on_progress=_scoped_progress(on_progress, f"transcription:{instrument}"),
        )

        export_stage = f"export:{instrument}"
        on_progress(export_stage, 0.0)
        midi_path = target_dir / f"{input_path.stem}.{instrument}.mid"
        export_kwargs = {}
        if instrument == "guitar" and guitar_type is not None:
            export_kwargs["instrument_type"] = guitar_type
        export_fn(
            result.note_events,
            midi_path,
            bends=[note.bends for note in result.note_events.notes],
            **export_kwargs,
        )
        on_progress(export_stage, 100.0)

        summary.instruments.append(
            InstrumentSummary(
                instrument=instrument,
                note_count=len(result.note_events.notes),
                midi_path=str(midi_path),
                cache_hit=transcription_hit,
            )
        )

    return summary


ANALYSIS_STAGE = "analysis"

# Revision of the AnalysisResult contract as cached by run_analysis. Bump it
# whenever the schema changes; revision 2 added ``chords`` and
# ``key_confidence`` (ANA-TASK-02).
ANALYSIS_CONTRACT_REVISION = 2

# Stage names reported by run_analysis, in pipeline order.
ANALYSIS_STAGES = ("separation", "analysis:beats", "analysis:harmony")


def analysis_version() -> str:
    """Cache version string of the analysis stage.

    Combines the installed madmom distribution version (both the beats
    and the harmony models come from it), the Demucs model version (the
    harmony stage consumes its stems) and the AnalysisResult contract
    revision, so upgrading any of them invalidates cached analyses.
    """
    from importlib.metadata import PackageNotFoundError, version

    from tabgen.core.separation.demucs import MODEL_VERSION

    try:
        madmom_version = version("madmom")
    except PackageNotFoundError:  # pragma: no cover - env without madmom
        madmom_version = "unknown"
    return (
        f"madmom-{madmom_version}+{MODEL_VERSION}"
        f"+contract-{ANALYSIS_CONTRACT_REVISION}"
    )


@dataclass
class AnalysisSummary:
    """Overall outcome of :func:`run_analysis`."""

    input_path: str
    # True when the stems came from the separation cache. Also True on an
    # analysis cache hit: the stems were not even needed then.
    separation_cache_hit: bool
    # True when the whole AnalysisResult came from the analysis cache.
    analysis_cache_hit: bool
    result: AnalysisResult


def run_analysis(
    input_path: str | Path,
    device: str | None = None,
    on_progress: ProgressCallback = null_progress,
    cache: StageCache | None = None,
    separate_fn: _SeparateFn | None = None,
    beats_fn: _BeatsFn | None = None,
    harmony_fn: _HarmonyFn | None = None,
) -> AnalysisSummary:
    """Analyze the input: tempo/beats plus key/chords, with caching.

    Beats run on the original audio (madmom's downbeat tracker wants the
    percussion); harmony runs on the separation stems (it sums every
    non-drums stem). The merged :class:`AnalysisResult` is cached in
    ``.tabgen/`` next to the input under stage ``analysis`` and
    :func:`analysis_version`, so a second run touches neither Demucs nor
    madmom. The cache key hashes the input bytes and pins every model
    version, which fully determines the stems, so stem files need no
    separate validation here.

    Progress is reported on the stages in :data:`ANALYSIS_STAGES`, each
    reaching 100.0 (immediately, on a cache hit). ``separate_fn`` /
    ``beats_fn`` / ``harmony_fn`` default to the real stages and exist
    for dependency injection in tests.
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise PipelineError(f"input audio not found: {input_path}")
    if cache is None:
        cache = StageCache(input_path)

    version = analysis_version()
    cached = cache.get(ANALYSIS_STAGE, version)
    if cached is not None:
        try:
            result = AnalysisResult.from_dict(cached)
        except (TypeError, KeyError):
            result = None  # malformed entry: treat as a miss and recompute
        if result is not None:
            for stage in ANALYSIS_STAGES:
                on_progress(stage, 100.0)
            return AnalysisSummary(
                input_path=str(input_path),
                separation_cache_hit=True,
                analysis_cache_hit=True,
                result=result,
            )

    if separate_fn is None:
        from tabgen.core.separation.demucs import separate as separate_fn
    if beats_fn is None:
        from tabgen.core.analysis.beats import analyze_beats as beats_fn
    if harmony_fn is None:
        from tabgen.core.analysis.harmony import analyze_harmony as harmony_fn

    separation, separation_hit = separate_fn(
        input_path, device=device, on_progress=on_progress
    )
    beats = beats_fn(input_path, on_progress=on_progress)
    harmony = harmony_fn(separation.stems, on_progress=on_progress)

    result = AnalysisResult(
        tempo_bpm=beats.tempo_bpm,
        beat_times=list(beats.beat_times),
        downbeat_times=list(beats.downbeat_times),
        key=harmony.key,
        key_confidence=harmony.key_confidence,
        chords=list(harmony.chords),
    )
    cache.put(ANALYSIS_STAGE, version, result.to_dict())
    return AnalysisSummary(
        input_path=str(input_path),
        separation_cache_hit=separation_hit,
        analysis_cache_hit=False,
        result=result,
    )


# --------------------------------------------------------------------------
# Tablature (Phase 3): analysis + transcription -> key check -> quantization
# -> fretting -> TabScore cache -> export.

TABLATURE_STAGE = "tablature"

# Revision of the tablature assembly done here (chord-to-measure mapping,
# event ordering, cached payload layout). Bump it whenever that logic
# changes so cached TabScores are recomputed.
# Revision 2 runs the technique detectors (bends/slides, then legato) on the
# fretted events; revision 3 sets ``TabScore.instrument_type`` from the
# guitar type.
TABLATURE_PIPELINE_REVISION = 3

TABLATURE_INSTRUMENTS = ("guitar", "bass")

# Tuning presets per instrument: open-string MIDI pitches, low-to-high.
TUNING_PRESETS: dict[str, dict[str, list[int]]] = {
    "guitar": {
        "standard": [40, 45, 50, 55, 59, 64],
        "drop-d": [38, 45, 50, 55, 59, 64],
        "half-step-down": [39, 44, 49, 54, 58, 63],
        "d-standard": [38, 43, 48, 53, 57, 62],
    },
    "bass": {
        "standard": [28, 33, 38, 43],
        "drop-d": [26, 33, 38, 43],
        "half-step-down": [27, 32, 37, 42],
        "five-string": [23, 28, 33, 38, 43],
    },
}

# Output formats of the export stage and the file suffixes that imply them.
EXPORT_FORMATS = ("gp5", "musicxml", "ascii")
_FORMAT_BY_SUFFIX = {
    ".gp5": "gp5",
    ".musicxml": "musicxml",
    ".xml": "musicxml",
    ".txt": "ascii",
}

_NOTE_CLASSES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _note_name_to_midi(token: str) -> int:
    """Parse ``E2`` / ``F#3`` / ``Bb1`` (scientific pitch) into MIDI."""
    letter = token[:1].upper()
    if letter not in _NOTE_CLASSES:
        raise PipelineError(f"invalid note name in tuning: {token!r}")
    rest = token[1:]
    alter = 0
    while rest[:1] in ("#", "b"):
        alter += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    try:
        octave = int(rest)
    except ValueError as err:
        raise PipelineError(f"invalid note name in tuning: {token!r}") from err
    return 12 * (octave + 1) + _NOTE_CLASSES[letter] + alter


def resolve_tuning(spec: str | Sequence[int] | None, instrument: str) -> list[int]:
    """Turn a tuning spec into open-string MIDI pitches, low-to-high.

    ``spec`` is ``None`` (standard tuning), a preset name from
    :data:`TUNING_PRESETS` (e.g. ``"drop-d"``), a comma-separated list of
    note names or MIDI numbers ordered low-to-high (``"D2,A2,D3,G3,B3,E4"``
    or ``"38,45,50,55,59,64"``), or a sequence of MIDI ints.
    """
    presets = TUNING_PRESETS.get(instrument)
    if presets is None:
        raise PipelineError(f"no tuning presets for instrument {instrument!r}")
    if spec is None:
        return list(presets["standard"])
    if not isinstance(spec, str):
        tuning = [int(p) for p in spec]
    elif spec.strip().lower() in presets:
        return list(presets[spec.strip().lower()])
    else:
        tokens = [t.strip() for t in spec.split(",") if t.strip()]
        tuning = [int(t) if t.lstrip("-").isdigit() else _note_name_to_midi(t)
                  for t in tokens]
    if len(tuning) < 1:
        raise PipelineError(f"empty tuning for {instrument}: {spec!r}")
    if tuning != sorted(tuning):
        raise PipelineError(
            f"tuning must be ordered low-to-high (thickest string first): {spec!r}"
        )
    return tuning


def resolve_export_format(output_path: str | Path, fmt: str | None = None) -> str:
    """Pick the export format: ``fmt`` when given, else from the suffix."""
    if fmt is not None:
        fmt = fmt.lower()
        if fmt not in EXPORT_FORMATS:
            raise PipelineError(
                f"unknown export format {fmt!r}; choose one of "
                f"{', '.join(EXPORT_FORMATS)}"
            )
        return fmt
    suffix = Path(output_path).suffix.lower()
    if suffix not in _FORMAT_BY_SUFFIX:
        raise PipelineError(
            f"cannot infer the export format from {Path(output_path).name!r}; "
            f"use a .gp5, .musicxml/.xml or .txt suffix, or pass a format"
        )
    return _FORMAT_BY_SUFFIX[suffix]


class _AnalysisFn(Protocol):
    def __call__(
        self,
        input_path: Path,
        device: Optional[str] = None,
        on_progress: ProgressCallback = null_progress,
        cache: StageCache | None = None,
    ) -> AnalysisSummary: ...


class _FrettingFn(Protocol):
    def __call__(self, notes, config=None, chords=None): ...


@dataclass
class TablatureSummary:
    """Overall outcome of :func:`run_tablature`."""

    input_path: str
    output_path: str
    format: str
    # True when the TabScores came from the tablature cache (no Demucs,
    # Basic Pitch, madmom or fretting DP ran).
    cache_hit: bool
    scores: list[TabScore] = field(default_factory=list)
    # Per score, subdivisions_in_beat of each event (4 straight, 3 triplet),
    # parallel to that score's events.
    beat_grids: list[list[int]] = field(default_factory=list)
    # Outcome of the key cross-check (asdict of KeyCheckResult).
    key_check: dict = field(default_factory=dict)
    # Per instrument, how many transcribed notes could not be fretted.
    unassigned: dict[str, int] = field(default_factory=dict)


def _check_guitar_type(guitar_type: str | None) -> None:
    """Raise PipelineError unless ``guitar_type`` is None or a known type."""
    from tabgen.core.models import GUITAR_TYPES

    if guitar_type is not None and guitar_type not in GUITAR_TYPES:
        raise PipelineError(
            f"unknown guitar type {guitar_type!r}; choose one of "
            f"{', '.join(GUITAR_TYPES)}"
        )


def _fretting_configs(
    instruments: Sequence[str],
    tunings: Mapping[str, Sequence[int]],
    capos: Mapping[str, int],
    guitar_type: str = DEFAULT_GUITAR_TYPE,
):
    """Per-instrument FrettingConfig; the guitar's max fret follows its type."""
    from tabgen.core.fretting import FrettingConfig, guitar_config

    configs = {}
    for name in instruments:
        tuning = list(tunings[name])
        capo = int(capos.get(name, 0))
        if name == "guitar":
            configs[name] = guitar_config(
                guitar_type, tuning_midi=tuning, capo_fret=capo
            )
        else:
            configs[name] = FrettingConfig(tuning_midi=tuning, capo_fret=capo)
    return configs


def _techniques_tag(techniques: bool) -> str:
    """Cache tag of the technique switch and the detector thresholds."""
    if not techniques:
        return "tech-off"
    import hashlib
    import json
    from dataclasses import asdict

    from tabgen.core.techniques import BendConfig, LegatoConfig

    params = {"bends": asdict(BendConfig()), "legato": asdict(LegatoConfig())}
    digest = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    return f"tech-{digest}"


def tablature_version(
    configs: Mapping[str, object],
    techniques: bool = True,
    guitar_type: str = DEFAULT_GUITAR_TYPE,
    transcriber: str = DEFAULT_TRANSCRIBER,
) -> str:
    """Cache version of the tablature stage for the given fretting configs.

    Pins the TabScore contract (``TAB_FORMAT_VERSION``), this assembly's
    revision, every upstream model (analysis, Basic Pitch), the Note
    contract revision, a digest of the per-instrument fretting parameters
    (tuning — hence the string count, e.g. the 5-string bass preset —,
    capo, max fret, weights), the guitar type (``gtype-...``: it is stored
    in ``TabScore.instrument_type`` even when two types share a max fret)
    and the technique switch (``tech-off``, or a digest of the bend/slide
    and legato detector thresholds), so changing any of them recomputes the
    tablature. A guitar transcribed by ``riley`` adds
    :func:`transcriber_tag` (transcriber and weights sha); ``basic-pitch``
    adds nothing, so its keys are unchanged.
    """
    import hashlib
    import json
    from dataclasses import asdict

    from tabgen.core.models import NOTE_CONTRACT_REVISION
    from tabgen.core.transcription.basic_pitch import MODEL_VERSION as BP_VERSION

    params = {name: asdict(cfg) for name, cfg in sorted(configs.items())}
    digest = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    return (
        f"tab-{TAB_FORMAT_VERSION}+rev-{TABLATURE_PIPELINE_REVISION}"
        f"+{analysis_version()}+{BP_VERSION}"
        f"{transcriber_tag(transcriber, list(configs))}"
        f"+note-{NOTE_CONTRACT_REVISION}"
        f"+params-{digest}+gtype-{guitar_type}+{_techniques_tag(techniques)}"
    )


def _measure_chords(
    chords: Sequence[ChordSegment],
    beat_times: Sequence[float],
    downbeat_times: Sequence[float],
    beats_per_measure: int,
) -> list[MeasureChord]:
    """Attach each chord change to the measure where it starts.

    Chord onsets are quantized on the same grid as the notes, so measure
    numbers line up with the events. Only changes are annotated: a chord
    equal to the previous annotation is skipped, ``"N"`` is never
    annotated, and when several changes start in one measure the first wins.
    """
    from tabgen.core.export.quantize import quantize_notes

    segments = [c for c in chords if c.label != "N"]
    if not segments:
        return []
    pseudo = [Note(pitch_midi=0, start_s=c.start_s, end_s=c.end_s) for c in segments]
    placed = quantize_notes(
        pseudo,
        beat_times,
        downbeat_times,
        beats_per_measure=beats_per_measure,
        detect_triplets=False,
    )
    # quantize_notes returns notes sorted by position, not input order.
    label_by_time = {(c.start_s, c.end_s): c.label for c in segments}
    result: list[MeasureChord] = []
    previous_label = None
    for q in placed:
        label = label_by_time[(q.start_s, q.end_s)]
        if result and result[-1].measure == q.measure:
            continue
        if label == previous_label:
            continue
        result.append(MeasureChord(measure=q.measure, label=label))
        previous_label = label
    return result


def export_tablature(
    scores: Sequence[TabScore],
    output_path: str | Path,
    fmt: str,
    beat_grids: Sequence[Sequence[int]] | None = None,
    title: str = "",
) -> Path:
    """Write ``scores`` in ``fmt`` (one of :data:`EXPORT_FORMATS`)."""
    if fmt == "gp5":
        from tabgen.core.export.gp5 import export_gp5

        return export_gp5(scores, output_path, beat_grids=beat_grids, title=title)
    if fmt == "musicxml":
        from tabgen.core.export.musicxml import export_musicxml

        return export_musicxml(
            scores, output_path, beat_grids=beat_grids, title=title
        )
    if fmt == "ascii":
        from tabgen.core.export.ascii_tab import export_ascii_tab

        return export_ascii_tab(scores, output_path, beat_grids=beat_grids)
    raise PipelineError(f"unknown export format {fmt!r}")


def _tablature_stages(instruments: Sequence[str]) -> list[str]:
    """Stage names run_tablature reports before export, in pipeline order."""
    return [
        *ANALYSIS_STAGES,
        *(f"transcription:{name}" for name in instruments),
        "key_check",
        "quantization",
        *(f"fretting:{name}" for name in instruments),
    ]


def run_tablature(
    input_path: str | Path,
    output_path: str | Path | None = None,
    fmt: str | None = None,
    instruments: Sequence[str] = TABLATURE_INSTRUMENTS,
    tunings: Mapping[str, Sequence[int]] | None = None,
    capos: Mapping[str, int] | None = None,
    device: str | None = None,
    on_progress: ProgressCallback = null_progress,
    cache: StageCache | None = None,
    separate_fn: _SeparateFn | None = None,
    transcribe_fn: _TranscribeFn | None = None,
    analysis_fn: _AnalysisFn | None = None,
    fretting_fn: _FrettingFn | None = None,
    techniques: bool = True,
    guitar_type: str = DEFAULT_GUITAR_TYPE,
    transcriber: str = DEFAULT_TRANSCRIBER,
) -> TablatureSummary:
    """Build guitar/bass tablature for the input and export it.

    Chains, with caching: :func:`run_analysis` (separation, beats, key and
    chords), Basic Pitch transcription of each instrument's stem, the key
    cross-check against the transcribed notes, quantization on the beat
    grid and string/fret assignment by the fretting DP. The resulting
    :class:`TabScore` list is cached in ``.tabgen/`` under stage
    ``tablature`` and :func:`tablature_version` (which pins tunings, capo
    and fretting weights), so a second run with the same parameters skips
    Demucs, Basic Pitch, madmom and the DP entirely. Export always runs
    (it is cheap), to ``output_path`` (default ``<input>.gp5``) in ``fmt``
    or the format implied by the suffix.

    ``tunings`` / ``capos`` map instrument names to open-string MIDI
    pitches (low-to-high) and capo fret; missing entries use the standard
    tuning and no capo. Progress is reported per stage (see
    :func:`_tablature_stages`, plus ``export``), each reaching 100.0.
    ``separate_fn`` / ``transcribe_fn`` / ``analysis_fn`` /
    ``fretting_fn`` default to the real stages and exist for dependency
    injection in tests.

    ``techniques`` (default on) runs the technique detectors on the fretted
    events of each instrument, bends/slides first and legato second (the
    call order is the precedence: a detector never overwrites a technique
    already set), so exporters write bends, slides, hammer-ons and
    pull-offs. When off, every ``TabNote.technique`` stays ``None`` and the
    output carries no effect. The switch is part of the cache version.

    ``guitar_type`` (one of ``models.GUITAR_TYPES``: electric, nylon,
    steel) sets the guitar's fretting limits (max fret, see
    ``fretting.dp.GUITAR_MAX_FRETS``) and its ``TabScore.instrument_type``,
    from which the exporters take the General MIDI program. It is part of
    the cache version.

    ``transcriber`` (one of :data:`TRANSCRIBERS`) picks the guitar's
    transcription when ``transcribe_fn`` is not injected: ``riley`` gives
    Riley notes with Basic Pitch bends (see :func:`default_transcribe_fn`),
    the bass stays on Basic Pitch. It is part of the cache version.
    """
    input_path = Path(input_path)
    _check_guitar_type(guitar_type)
    _check_transcriber(transcriber)
    if not input_path.is_file():
        raise PipelineError(f"input audio not found: {input_path}")
    instruments = tuple(instruments)
    if not instruments:
        raise PipelineError("no instruments requested")
    unknown = [name for name in instruments if name not in TABLATURE_INSTRUMENTS]
    if unknown:
        raise PipelineError(
            f"unsupported instrument(s) {', '.join(unknown)}; choose from "
            f"{', '.join(TABLATURE_INSTRUMENTS)}"
        )
    if output_path is None:
        output_path = input_path.with_suffix(".gp5")
    output_path = Path(output_path)
    fmt = resolve_export_format(output_path, fmt)
    if cache is None:
        cache = StageCache(input_path)

    tunings = dict(tunings or {})
    capos = dict(capos or {})
    for name in instruments:
        tunings.setdefault(name, resolve_tuning(None, name))
    configs = _fretting_configs(instruments, tunings, capos, guitar_type)
    version = tablature_version(
        configs, techniques=techniques, guitar_type=guitar_type,
        transcriber=transcriber,
    )

    summary = None
    cached = cache.get(TABLATURE_STAGE, version)
    if cached is not None:
        try:
            summary = TablatureSummary(
                input_path=str(input_path),
                output_path=str(output_path),
                format=fmt,
                cache_hit=True,
                scores=[TabScore.from_dict(s) for s in cached["scores"]],
                beat_grids=[list(g) for g in cached["beat_grids"]],
                key_check=dict(cached["key_check"]),
                unassigned=dict(cached["unassigned"]),
            )
        except (TypeError, KeyError):
            summary = None  # malformed entry: treat as a miss and recompute
        if summary is not None:
            for stage in _tablature_stages(instruments):
                on_progress(stage, 100.0)

    if summary is None:
        summary = _compute_tablature(
            input_path,
            output_path,
            fmt,
            instruments,
            configs,
            device,
            on_progress,
            cache,
            separate_fn,
            transcribe_fn,
            analysis_fn,
            fretting_fn,
            techniques,
            guitar_type,
            transcriber,
        )
        cache.put(
            TABLATURE_STAGE,
            version,
            {
                "scores": [s.to_dict() for s in summary.scores],
                "beat_grids": summary.beat_grids,
                "key_check": summary.key_check,
                "unassigned": summary.unassigned,
            },
        )

    on_progress("export", 0.0)
    export_tablature(
        summary.scores,
        output_path,
        fmt,
        beat_grids=summary.beat_grids,
        title=input_path.stem,
    )
    on_progress("export", 100.0)
    return summary


def _onset_key(q) -> tuple[int, int, float]:
    """Quantized onset of a note, comparable across straight/triplet beats."""
    return (q.measure, q.beat, q.subdivision / q.subdivisions_in_beat)


def _fretting_input(quantized: Sequence) -> tuple[dict, list[Note]]:
    """Build the fretting DP input from quantized notes.

    Notes that quantize onto the same onset must be one chord frame for the
    DP (otherwise two of them can land on the same string, which a tab
    cannot play nor a .gp5 beat encode), so each group gets one canonical
    ``start_s``: the earliest original onset of the group. A pitch repeated
    within a group keeps only its longest note. Returns the Note copies and
    a map from ``id(note)`` back to its quantized note; ``FrettedNote.note``
    keeps that identity.
    """
    groups: dict[tuple[int, int, float], dict[int, object]] = {}
    for q in quantized:
        by_pitch = groups.setdefault(_onset_key(q), {})
        kept = by_pitch.get(q.pitch_midi)
        if kept is None or (
            q.duration_subdivisions / q.subdivisions_in_beat
            > kept.duration_subdivisions / kept.subdivisions_in_beat
        ):
            by_pitch[q.pitch_midi] = q
    by_id: dict[int, object] = {}
    notes: list[Note] = []
    for by_pitch in groups.values():
        start_s = min(q.start_s for q in by_pitch.values())
        for q in by_pitch.values():
            note = Note(
                pitch_midi=q.pitch_midi,
                start_s=start_s,
                end_s=max(q.end_s, start_s),
                velocity=q.velocity,
                confidence=q.confidence,
            )
            by_id[id(note)] = q
            notes.append(note)
    return by_id, notes


def _source_notes(transcribed: Sequence[Note], placed: Sequence) -> list[Note]:
    """Transcribed Note behind each placed (quantized, fretted) pair.

    ``QuantizedNote`` and the fretting copies built by
    :func:`_fretting_input` drop ``Note.bends``, but the quantized note keeps
    the original ``pitch_midi``/``start_s``/``end_s`` verbatim, so that
    triple maps it back to the transcribed note (identical triples are the
    same note for every detector). A pair with no match (not expected)
    falls back to a bend-less copy of the quantized note.
    """
    by_key: dict[tuple[int, float, float], Note] = {}
    for note in transcribed:
        by_key.setdefault((note.pitch_midi, note.start_s, note.end_s), note)
    sources: list[Note] = []
    for q, _ in placed:
        note = by_key.get((q.pitch_midi, q.start_s, q.end_s))
        if note is None:
            note = Note(
                pitch_midi=q.pitch_midi,
                start_s=q.start_s,
                end_s=q.end_s,
                velocity=q.velocity,
                confidence=q.confidence,
            )
        sources.append(note)
    return sources


def _detect_techniques(events: list[TabNote], sources: list[Note]) -> list[TabNote]:
    """Fill techniques: bends/slides first, then legato (call order = precedence)."""
    from tabgen.core.techniques import detect_bends_and_slides, detect_legato

    events = detect_bends_and_slides(events, sources)
    return detect_legato(events, sources)


def _compute_tablature(
    input_path: Path,
    output_path: Path,
    fmt: str,
    instruments: tuple[str, ...],
    configs: Mapping,
    device: str | None,
    on_progress: ProgressCallback,
    cache: StageCache,
    separate_fn: _SeparateFn | None,
    transcribe_fn: _TranscribeFn | None,
    analysis_fn: _AnalysisFn | None,
    fretting_fn: _FrettingFn | None,
    techniques: bool = True,
    guitar_type: str = DEFAULT_GUITAR_TYPE,
    transcriber: str = DEFAULT_TRANSCRIBER,
) -> TablatureSummary:
    """Run every upstream stage and assemble the TabScores (cache miss)."""
    from dataclasses import asdict

    from tabgen.core.analysis.key_check import check_key
    from tabgen.core.export.quantize import _infer_beats_per_measure, quantize_notes

    if separate_fn is None:
        from tabgen.core.separation.demucs import separate as separate_fn
    if transcribe_fn is None:
        transcribe_fn = default_transcribe_fn(transcriber, device)
    if fretting_fn is None:
        from tabgen.core.fretting import assign_frets as fretting_fn

    if analysis_fn is None:
        injected_separate = separate_fn

        def analysis_fn(input_path, device=None, on_progress=null_progress, cache=None):
            return run_analysis(
                input_path,
                device=device,
                on_progress=on_progress,
                cache=cache,
                separate_fn=injected_separate,
            )

    analysis = analysis_fn(
        input_path, device=device, on_progress=on_progress, cache=cache
    ).result
    if len(analysis.beat_times) < 2:
        raise PipelineError(
            f"analysis found {len(analysis.beat_times)} beat(s); at least two "
            "are needed to build the measure grid"
        )

    # Stems come from the separation cache, already warmed by the analysis.
    separation, _ = separate_fn(input_path, device=device, on_progress=on_progress)
    missing = [name for name in instruments if name not in separation.stems]
    if missing:
        available = ", ".join(sorted(separation.stems)) or "none"
        raise PipelineError(
            f"no stem for instrument(s) {', '.join(missing)}; "
            f"available stems: {available}"
        )

    events_by_instrument: dict[str, NoteEvents] = {}
    for name in instruments:
        result, _ = transcribe_fn(
            Path(separation.stems[name]),
            instrument=name,
            on_progress=_scoped_progress(on_progress, f"transcription:{name}"),
        )
        events_by_instrument[name] = result.note_events

    on_progress("key_check", 0.0)
    key_result = check_key(
        analysis.key, analysis.key_confidence, events_by_instrument.values()
    )
    on_progress("key_check", 100.0)

    on_progress("quantization", 0.0)
    beats_per_measure = _infer_beats_per_measure(
        sorted(analysis.beat_times), analysis.downbeat_times
    )
    quantized = {
        name: quantize_notes(
            events.notes,
            analysis.beat_times,
            analysis.downbeat_times,
            beats_per_measure=beats_per_measure,
        )
        for name, events in events_by_instrument.items()
    }
    measure_chords = _measure_chords(
        analysis.chords,
        analysis.beat_times,
        analysis.downbeat_times,
        beats_per_measure,
    )
    on_progress("quantization", 100.0)

    summary = TablatureSummary(
        input_path=str(input_path),
        output_path=str(output_path),
        format=fmt,
        cache_hit=False,
        key_check=asdict(key_result),
    )
    for name in instruments:
        stage = f"fretting:{name}"
        on_progress(stage, 0.0)
        by_id, notes = _fretting_input(quantized[name])
        fretted = fretting_fn(notes, configs[name], analysis.chords)
        placed = sorted(
            ((by_id[id(f.note)], f) for f in fretted.assignments),
            key=lambda pair: (
                pair[0].measure,
                pair[0].beat,
                pair[0].subdivision / pair[0].subdivisions_in_beat,
                pair[1].string,
            ),
        )
        config = configs[name]
        events = [
            TabNote(
                string=f.string,
                fret=f.fret,
                measure=q.measure,
                beat=q.beat,
                subdivision=q.subdivision,
                duration_subdivisions=q.duration_subdivisions,
                start_s=q.start_s,
                end_s=q.end_s,
            )
            for q, f in placed
        ]
        if techniques:
            sources = _source_notes(events_by_instrument[name].notes, placed)
            events = _detect_techniques(events, sources)
        summary.scores.append(
            TabScore(
                instrument=name,
                instrument_type=guitar_type if name == "guitar" else "",
                tuning_midi=list(config.tuning_midi),
                capo_fret=config.capo_fret,
                tempo_bpm=analysis.tempo_bpm,
                key=key_result.key,
                time_signature=[beats_per_measure, 4],
                events=events,
                chords=list(measure_chords),
            )
        )
        summary.beat_grids.append([q.subdivisions_in_beat for q, _ in placed])
        summary.unassigned[name] = len(fretted.unassigned)
        on_progress(stage, 100.0)
    return summary
