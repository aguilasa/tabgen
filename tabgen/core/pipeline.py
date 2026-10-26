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
from tabgen.core.models import AnalysisResult

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
    def __call__(self, note_events, output_path: Path, bends=None) -> Path: ...


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
    """
    input_path = Path(input_path)
    if not instruments:
        raise PipelineError("no instruments requested")

    if separate_fn is None:
        from tabgen.core.separation.demucs import separate as separate_fn
    if transcribe_fn is None:
        from tabgen.core.transcription.basic_pitch import transcribe as transcribe_fn
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
        export_fn(result.note_events, midi_path, bends=result.bends)
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
