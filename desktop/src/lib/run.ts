// One `tablature` job of the workspace: request arguments from the
// generation options (drawer, remembered per song), live per-stage progress from the worker's NDJSON events, cancel by
// killing the worker (the core has no cooperative cancellation).
import { useCallback, useEffect, useRef, useState } from "react";
import { deviceArg, type Device, type Prefs } from "./prefs";
import { baseName } from "./recents";
import { CANCELLED, cancelWorker, runWorker, WorkerError } from "./worker";

/** `tablature` result line (tabgen/worker/__init__.py), without `type`. */
export interface TablatureResult {
  input_path: string;
  output_path: string;
  format: string;
  /** True when the TabScores came from the tablature cache. */
  cache_hit: boolean;
  scores: Record<string, unknown>[];
  beat_grids: number[][];
  key_check: { key?: string; key_confidence?: number; switched?: boolean } & Record<
    string,
    unknown
  >;
  unassigned: Record<string, number>;
  ascii_preview: string;
  /** Per score, in the same order: display summary computed by the worker. */
  tracks: TrackSummary[];
}

/** One `tracks` item of the tablature result. */
export interface TrackSummary {
  instrument: string;
  instrument_type: string;
  note_count: number;
  /** TUNING_PRESETS name, "" for a custom tuning. */
  tuning_name: string;
  /** Scientific pitch names, low-to-high. */
  tuning_notes: string[];
  capo_fret: number;
  unassigned: number;
  /** Technique kind -> number of events. */
  techniques: Record<string, number>;
}

export interface ChordSegment {
  start_s: number;
  end_s: number;
  /** Harte label; "N" = no chord. */
  label: string;
}

/** `analyze` result line, without `type`. */
export interface AnalysisPayload {
  input_path: string;
  separation_cache_hit: boolean;
  analysis_cache_hit: boolean;
  result: {
    tempo_bpm: number;
    beat_times: number[];
    downbeat_times: number[];
    key: string;
    key_confidence: number;
    chords: ChordSegment[];
  };
  /** Stem name -> wav path; {} when the separation cache no longer holds them. */
  stems: Record<string, string>;
}

/** `transcribe` result line, without `type`. */
export interface TranscriptionPayload {
  input_path: string;
  separation_cache_hit: boolean;
  instruments: {
    instrument: string;
    note_count: number;
    midi_path: string;
    cache_hit: boolean;
    transcriber: string;
  }[];
}

/** Progress of one core stage, as reported by the worker. */
export interface StageProgress {
  name: string;
  pct: number;
  /** First event already at 100: the core took it from the cache. */
  cached: boolean;
  /** Arrival order, tie-break inside the same display rank. */
  seq: number;
}

export type RunPhase = "running" | "cancelling" | "done" | "error" | "cancelled";

export interface RunState {
  path: string;
  jobId: string;
  phase: RunPhase;
  /** Stages in display order, created as their first event arrives. */
  stages: StageProgress[];
  startedAt: number;
  endedAt: number | null;
  /** Worker args of the job (exports and the detail jobs reuse them). */
  args: Record<string, unknown>;
  result: TablatureResult | null;
  error: { kind: string; message: string; stderr: string } | null;
}

function isExport(stage: string): boolean {
  return stage === "export" || stage.startsWith("export:");
}

// Display order only; the stage names themselves come from the events.
const DISPLAY_ORDER: ((stage: string) => boolean)[] = [
  (s) => s === "separation",
  (s) => s.startsWith("analysis:"),
  (s) => s.startsWith("transcription:"),
  (s) => s === "key_check",
  (s) => s === "quantization",
  (s) => s.startsWith("fretting:"),
  isExport,
];

function displayRank(stage: string): number {
  const rank = DISPLAY_ORDER.findIndex((matches) => matches(stage));
  return rank === -1 ? DISPLAY_ORDER.length : rank;
}

export function withProgress(stages: StageProgress[], name: string, pct: number): StageProgress[] {
  const index = stages.findIndex((s) => s.name === name);
  if (index !== -1) {
    const current = stages[index];
    const next = stages.slice();
    next[index] = { ...current, pct, cached: current.cached && pct >= 100 };
    return next;
  }
  const added = [...stages, { name, pct, cached: pct >= 100, seq: stages.length }];
  return added.sort((a, b) => displayRank(a.name) - displayRank(b.name) || a.seq - b.seq);
}

export type CardStatus = "pending" | "cache" | "running" | "ok" | "error" | "cancelled";

export interface StageCard {
  title: string;
  matches: (stage: string) => boolean;
}

/** Workspace cards and the core stages each one summarizes. */
export const STAGE_CARDS: StageCard[] = [
  { title: "Separação", matches: (s) => s === "separation" },
  { title: "Análise", matches: (s) => s.startsWith("analysis:") },
  {
    title: "Transcrição",
    matches: (s) => s.startsWith("transcription:") || s === "key_check",
  },
  {
    title: "Tablatura",
    matches: (s) =>
      s === "quantization" || s.startsWith("fretting:") || isExport(s),
  },
];

function cardOf(stage: string): number {
  return STAGE_CARDS.findIndex((card) => card.matches(stage));
}

/**
 * Card where a failed or cancelled run stopped: the card of the first
 * unfinished stage, else the one after the last card that got events (the
 * job died before the next stage reported), the first card when none did.
 */
function stoppedCard(run: RunState): number {
  const unfinished = run.stages.find((s) => s.pct < 100);
  if (unfinished) return cardOf(unfinished.name);
  const reached = Math.max(-1, ...run.stages.map((s) => cardOf(s.name)));
  return Math.min(reached + 1, STAGE_CARDS.length - 1);
}

/** Card state derived from the stages of the run that belong to it. */
export function cardStatus(run: RunState | null, cardIndex: number): CardStatus {
  if (!run) return "pending";
  const card = STAGE_CARDS[cardIndex];
  const own = run.stages.filter((s) => card.matches(s.name));
  const stopped = run.phase === "error" || run.phase === "cancelled";
  if (stopped && cardIndex === stoppedCard(run)) {
    return run.phase === "error" ? "error" : "cancelled";
  }
  if (own.length === 0) return "pending";
  const laterStarted = run.stages.some((s) => cardOf(s.name) > cardIndex);
  const finished =
    own.every((s) => s.pct >= 100) && (laterStarted || run.phase === "done" || stopped);
  // export always runs (the core does not cache it): it does not decide "cache"
  const cacheable = own.filter((s) => !isExport(s.name));
  if (finished) return cacheable.length > 0 && cacheable.every((s) => s.cached) ? "cache" : "ok";
  return stopped ? "pending" : "running";
}

function stemOf(path: string): string {
  const name = baseName(path);
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(0, dot) : name;
}

/** `presets` result line (tabgen/worker/__init__.py): option values from the core. */
export interface GenerationPresets {
  instruments: string[];
  /** Instrument -> TUNING_PRESETS in core order. */
  tunings: Record<string, { name: string; midi: number[]; notes: string[] }[]>;
  /** Instrument -> preset name used when no tuning is given. */
  default_tunings: Record<string, string>;
  guitar_types: string[];
  default_guitar_type: string;
  transcribers: string[];
  default_transcriber: string;
  /** EXPORT_FORMATS with the suffixes that imply each one (first = written). */
  export_formats: { format: string; suffixes: string[] }[];
  /** [min, max] capo fret. */
  capo_range: [number, number];
}

/** `tuning` result line: one tuning resolved by the core's resolve_tuning. */
export interface ResolvedTuning {
  instrument: string;
  midi: number[];
  notes: string[];
  /** TUNING_PRESETS name with the same pitches, "" when custom. */
  name: string;
}

/** Value of a tuning select that means "use the custom text". */
export const CUSTOM_TUNING = "custom";

/** Choices of the "Gerar tab" drawer, remembered per song. */
export interface GenOptions {
  /** Selected instruments, in TABLATURE_INSTRUMENTS order. */
  instruments: string[];
  /** Instrument -> preset name, or CUSTOM_TUNING. */
  tuning: Record<string, string>;
  /** Instrument -> custom tuning text (notes or MIDI, low-to-high). */
  customTuning: Record<string, string>;
  /** Guitar capo fret. */
  capo: number;
  guitarType: string;
  transcriber: string;
  techniques: boolean;
  device: Device;
  /** Output file; its suffix and `format` agree unless the suffix is unknown. */
  output: string;
  format: string;
}

/** Format implied by the suffix of `path`, or null when no format claims it. */
export function formatOfPath(presets: GenerationPresets, path: string): string | null {
  const name = baseName(path).toLowerCase();
  const dot = name.lastIndexOf(".");
  if (dot <= 0) return null;
  const suffix = name.slice(dot);
  return presets.export_formats.find((f) => f.suffixes.includes(suffix))?.format ?? null;
}

/** `path` with the suffix written for `format` (a known suffix is replaced). */
export function withFormatSuffix(
  presets: GenerationPresets,
  path: string,
  format: string,
): string {
  const suffix = presets.export_formats.find((f) => f.format === format)?.suffixes[0];
  if (!suffix) return path;
  const base = formatOfPath(presets, path) ? path.slice(0, path.lastIndexOf(".")) : path;
  return base + suffix;
}

/** Default output: `<stem>.gp5` in prefs.outputDir, else next to the audio. */
export function defaultOutput(path: string, prefs: Prefs): string {
  const dir = prefs.outputDir.trim().replace(/\/+$/, "") || dirName(path);
  return `${dir}/${stemOf(path)}.gp5`;
}

/** Options of a song never generated: core defaults, device/transcriber/folder from prefs. */
export function defaultOptions(
  path: string,
  prefs: Prefs,
  presets: GenerationPresets,
): GenOptions {
  return {
    instruments: [...presets.instruments],
    tuning: { ...presets.default_tunings },
    customTuning: {},
    capo: presets.capo_range[0],
    guitarType: presets.default_guitar_type,
    transcriber: presets.transcribers.includes(prefs.transcriber)
      ? prefs.transcriber
      : presets.default_transcriber,
    techniques: true,
    device: prefs.device,
    output: defaultOutput(path, prefs),
    format: "gp5",
  };
}

/** Worker spec of an instrument's tuning: the preset name or the custom text. */
export function tuningSpec(options: GenOptions, instrument: string): string | undefined {
  const choice = options.tuning[instrument];
  if (choice === CUSTOM_TUNING) return options.customTuning[instrument] ?? "";
  return choice || undefined;
}

/**
 * Worker args for `tablature`. Without options (no drawer yet): device and
 * transcriber from the prefs, output in prefs.outputDir as `<stem>.gp5` or
 * the worker default (`<input>.gp5`, next to the audio).
 */
export function tablatureArgs(
  path: string,
  prefs: Prefs,
  options?: GenOptions,
): Record<string, unknown> {
  if (!options) {
    const args: Record<string, unknown> = { input: path, transcriber: prefs.transcriber };
    const device = deviceArg(prefs.device);
    if (device) args.device = device;
    const dir = prefs.outputDir.trim().replace(/\/+$/, "");
    if (dir) args.output = `${dir}/${stemOf(path)}.gp5`;
    return args;
  }
  const args: Record<string, unknown> = {
    input: path,
    output: options.output.trim(),
    format: options.format,
    instruments: options.instruments,
    techniques: options.techniques,
    transcriber: options.transcriber,
  };
  const tunings: Record<string, string> = {};
  for (const name of options.instruments) {
    const spec = tuningSpec(options, name);
    if (spec !== undefined) tunings[name] = spec;
  }
  args.tunings = tunings;
  if (options.instruments.includes("guitar")) {
    args.capos = { guitar: options.capo };
    args.guitar_type = options.guitarType;
  }
  const device = deviceArg(options.device);
  if (device) args.device = device;
  return args;
}

/** Remembered generation of one song: its options and how long the run took. */
export interface SongMemory {
  options: GenOptions;
  /** Wall time of the last finished run with these options, in ms. */
  lastRunMs: number | null;
  /** True when that run came from the tablature cache. */
  lastRunCached: boolean;
}

const OPTIONS_KEY = "tabgen.songOptions";
const MAX_REMEMBERED = 50;

function loadMemories(): Record<string, SongMemory & { saved_at: string }> {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(OPTIONS_KEY) ?? "{}");
    return stored && typeof stored === "object" && !Array.isArray(stored)
      ? (stored as Record<string, SongMemory & { saved_at: string }>)
      : {};
  } catch {
    return {};
  }
}

/** Last options used for `path` (null = never generated here). */
export function loadSongMemory(path: string): SongMemory | null {
  return loadMemories()[path] ?? null;
}

/** Remember `memory` for `path`, keeping the MAX_REMEMBERED most recent songs. */
export function saveSongMemory(path: string, memory: SongMemory): void {
  const all = loadMemories();
  all[path] = { ...memory, saved_at: new Date().toISOString() };
  const kept = Object.entries(all)
    .sort(([, a], [, b]) => b.saved_at.localeCompare(a.saved_at))
    .slice(0, MAX_REMEMBERED);
  try {
    localStorage.setItem(OPTIONS_KEY, JSON.stringify(Object.fromEntries(kept)));
  } catch {
    // storage unavailable: the options stay for this session only
  }
}

/**
 * Cold-run estimate in seconds, scaled by the song duration from the
 * README "Expected runtimes" table: `export` of a 4 min 08 s song with no
 * cache took ~193 s on an RTX 3060 Laptop (separation, analysis,
 * transcription and tablature). A warm run (tablature cache) took < 1 s.
 */
export const README_COLD_EXPORT = { songSeconds: 248, runSeconds: 193 };

export function coldEstimateSeconds(durationS: number): number {
  return (durationS * README_COLD_EXPORT.runSeconds) / README_COLD_EXPORT.songSeconds;
}

/** Recents artifacts after a finished run. */
export function runArtifacts(result: TablatureResult): string[] {
  return ["stems", "análise", "notas", result.format];
}

function newJobId(): string {
  return typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `job-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/**
 * The workspace's single tablature job. It lives above the screens, so
 * leaving the workspace does not lose a running job.
 */
export function useTablatureRun(
  python: string,
  prefs: Prefs,
  onFinished: (path: string, result: TablatureResult, elapsedMs: number) => void,
) {
  const [run, setRun] = useState<RunState | null>(null);
  const active = useRef<RunState | null>(null);
  const finished = useRef(onFinished);
  useEffect(() => {
    finished.current = onFinished;
  }, [onFinished]);

  const update = useCallback((jobId: string, change: (r: RunState) => RunState) => {
    setRun((current) => (current && current.jobId === jobId ? change(current) : current));
  }, []);

  const start = useCallback(
    (path: string, options?: GenOptions) => {
      if (!python || active.current) return;
      const state: RunState = {
        path,
        jobId: newJobId(),
        phase: "running",
        stages: [],
        startedAt: performance.now(),
        endedAt: null,
        args: tablatureArgs(path, prefs, options),
        result: null,
        error: null,
      };
      active.current = state;
      setRun(state);
      const { jobId } = state;
      runWorker<TablatureResult>(
        python,
        "tablature",
        state.args,
        (stage, pct) => update(jobId, (r) => ({ ...r, stages: withProgress(r.stages, stage, pct) })),
        jobId,
      ).then(
        (result) => {
          const endedAt = performance.now();
          update(jobId, (r) => ({ ...r, phase: "done", endedAt, result }));
          finished.current(path, result, endedAt - state.startedAt);
        },
        (err: unknown) => {
          const error =
            err instanceof WorkerError ? err : new WorkerError("Error", String(err));
          update(jobId, (r) => ({
            ...r,
            phase: error.kind === CANCELLED ? "cancelled" : "error",
            endedAt: performance.now(),
            error: { kind: error.kind, message: error.message, stderr: error.stderr },
          }));
        },
      ).finally(() => {
        if (active.current?.jobId === jobId) active.current = null;
      });
    },
    [python, prefs, update],
  );

  const cancel = useCallback(() => {
    const current = active.current;
    if (!current) return;
    update(current.jobId, (r) => ({ ...r, phase: "cancelling" }));
    void cancelWorker(current.jobId);
  }, [update]);

  return { run, start, cancel };
}

export type Loadable<T> =
  | { state: "loading" }
  | { state: "ok"; data: T }
  | { state: "error"; kind: string; message: string };

/** Stems, analysis and per-instrument notes of a finished run. */
export interface RunDetails {
  jobId: string;
  analysis: Loadable<AnalysisPayload>;
  transcription: Loadable<TranscriptionPayload>;
}

function failure(err: unknown): { state: "error"; kind: string; message: string } {
  const error = err instanceof WorkerError ? err : new WorkerError("Error", String(err));
  return { state: "error", kind: error.kind, message: error.message };
}

/**
 * Worker args of the detail jobs, from the tablature job's args: `analyze`
 * takes input/device; `transcribe` also the transcriber and guitar type, and
 * writes the .mid files next to the tablature output.
 */
export function detailArgs(run: RunState): {
  analyze: Record<string, unknown>;
  transcribe: Record<string, unknown>;
} {
  const { input, device, transcriber, guitar_type, instruments } = run.args;
  const analyze: Record<string, unknown> = { input };
  if (device !== undefined) analyze.device = device;
  const transcribe: Record<string, unknown> = { ...analyze };
  if (transcriber !== undefined) transcribe.transcriber = transcriber;
  if (guitar_type !== undefined) transcribe.guitar_type = guitar_type;
  if (instruments !== undefined) transcribe.instruments = instruments;
  if (run.result) transcribe.output_dir = dirName(run.result.output_path);
  return { analyze, transcribe };
}

export function dirName(path: string): string {
  const cut = path.lastIndexOf("/");
  return cut > 0 ? path.slice(0, cut) : "/";
}

/**
 * Once a tablature job finishes, fetch what its result does not carry:
 * `analyze` (stems + AnalysisResult) then `transcribe` (.mid per instrument).
 * Both hit the stage caches the tablature job just filled.
 */
export function useRunDetails(python: string, run: RunState | null): RunDetails | null {
  const [details, setDetails] = useState<RunDetails | null>(null);
  const started = useRef<string | null>(null);
  const done = run?.phase === "done" ? run : null;

  useEffect(() => {
    if (!done || !python || started.current === done.jobId) return;
    started.current = done.jobId;
    const { jobId } = done;
    const args = detailArgs(done);
    const set = (change: (d: RunDetails) => RunDetails) =>
      setDetails((current) => (current?.jobId === jobId ? change(current) : current));
    setDetails({ jobId, analysis: { state: "loading" }, transcription: { state: "loading" } });
    void (async () => {
      try {
        const data = await runWorker<AnalysisPayload>(python, "analyze", args.analyze);
        set((d) => ({ ...d, analysis: { state: "ok", data } }));
      } catch (err) {
        set((d) => ({ ...d, analysis: failure(err) }));
      }
      try {
        const data = await runWorker<TranscriptionPayload>(python, "transcribe", args.transcribe);
        set((d) => ({ ...d, transcription: { state: "ok", data } }));
      } catch (err) {
        set((d) => ({ ...d, transcription: failure(err) }));
      }
    })();
  }, [done, python]);

  return details && run && details.jobId === run.jobId ? details : null;
}

export type ExportFormat = "gp5" | "musicxml" | "ascii";

const EXPORT_SUFFIX: Record<ExportFormat, string> = {
  gp5: ".gp5",
  musicxml: ".musicxml",
  ascii: ".txt",
};

/** One export of a finished run, re-invoking `tablature` with another format. */
export interface ExportState {
  jobId: string;
  format: ExportFormat;
  phase: "running" | "done" | "error";
  startedAt: number;
  endedAt: number | null;
  outputPath: string;
  cacheHit: boolean;
  error: string | null;
}

/** Output path of an export: the run's output with the format's suffix. */
export function exportPath(result: TablatureResult, format: ExportFormat): string {
  const out = result.output_path;
  const name = out.slice(out.lastIndexOf("/") + 1);
  const dot = name.lastIndexOf(".");
  const stem = dot > 0 ? out.slice(0, out.length - name.length + dot) : out;
  return stem + EXPORT_SUFFIX[format];
}

/**
 * Exports of the run shown in the workspace. Same args as the run, so the
 * worker takes the TabScores from the tablature cache and only exports.
 */
export function useExports(python: string, run: RunState | null) {
  const [exports, setExports] = useState<ExportState | null>(null);
  const done = run?.phase === "done" && run.result ? run : null;

  const start = useCallback(
    (format: ExportFormat) => {
      if (!done?.result || !python) return;
      const outputPath = exportPath(done.result, format);
      const state: ExportState = {
        jobId: done.jobId,
        format,
        phase: "running",
        startedAt: performance.now(),
        endedAt: null,
        outputPath,
        cacheHit: false,
        error: null,
      };
      setExports(state);
      const same = (e: ExportState | null) => e?.startedAt === state.startedAt;
      runWorker<TablatureResult>(python, "tablature", {
        ...done.args,
        output: outputPath,
        format,
      }).then(
        (result) =>
          setExports((e) =>
            same(e)
              ? {
                  ...state,
                  phase: "done",
                  endedAt: performance.now(),
                  outputPath: result.output_path,
                  cacheHit: result.cache_hit,
                }
              : e,
          ),
        (err: unknown) =>
          setExports((e) =>
            same(e)
              ? {
                  ...state,
                  phase: "error",
                  endedAt: performance.now(),
                  error: `${failure(err).kind}: ${failure(err).message}`,
                }
              : e,
          ),
      );
    },
    [done, python],
  );

  const current = exports && done && exports.jobId === done.jobId ? exports : null;
  return { current, start };
}
