// One `tablature` job of the workspace: request arguments from the prefs,
// live per-stage progress from the worker's NDJSON events, cancel by
// killing the worker (the core has no cooperative cancellation).
import { useCallback, useEffect, useRef, useState } from "react";
import { deviceArg, type Prefs } from "./prefs";
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

/**
 * Worker args for `tablature` with the default options: device and
 * transcriber from the prefs; output in prefs.outputDir as `<stem>.gp5`,
 * or the worker default (`<input>.gp5`, next to the audio).
 */
export function tablatureArgs(path: string, prefs: Prefs): Record<string, unknown> {
  const args: Record<string, unknown> = { input: path, transcriber: prefs.transcriber };
  const device = deviceArg(prefs.device);
  if (device) args.device = device;
  const dir = prefs.outputDir.trim().replace(/\/+$/, "");
  if (dir) args.output = `${dir}/${stemOf(path)}.gp5`;
  return args;
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
  onFinished: (path: string, result: TablatureResult) => void,
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
    (path: string) => {
      if (!python || active.current) return;
      const state: RunState = {
        path,
        jobId: newJobId(),
        phase: "running",
        stages: [],
        startedAt: performance.now(),
        endedAt: null,
        result: null,
        error: null,
      };
      active.current = state;
      setRun(state);
      const { jobId } = state;
      runWorker<TablatureResult>(
        python,
        "tablature",
        tablatureArgs(path, prefs),
        (stage, pct) => update(jobId, (r) => ({ ...r, stages: withProgress(r.stages, stage, pct) })),
        jobId,
      ).then(
        (result) => {
          update(jobId, (r) => ({ ...r, phase: "done", endedAt: performance.now(), result }));
          finished.current(path, result);
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
