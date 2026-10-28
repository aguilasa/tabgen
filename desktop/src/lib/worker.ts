// Client of the NDJSON worker (`python -m tabgen.worker`, protocol in
// tabgen/worker/__init__.py). One call = one worker process = one job.
import { Channel, invoke } from "@tauri-apps/api/core";

export type WorkerCmd = "doctor" | "analyze" | "transcribe" | "tablature";

export interface ProgressMessage {
  type: "progress";
  stage: string;
  pct: number;
}

export interface ResultMessage {
  type: "result";
  [key: string]: unknown;
}

export interface ErrorMessage {
  type: "error";
  kind: string;
  message: string;
}

type WorkerMessage = ProgressMessage | ResultMessage | ErrorMessage;

interface WorkerExit {
  code: number;
  stderr_tail: string;
}

/** A failed job: the worker's error line, or a process that could not run. */
export class WorkerError extends Error {
  readonly kind: string;
  readonly stderr: string;

  constructor(kind: string, message: string, stderr = "") {
    super(message);
    this.name = "WorkerError";
    this.kind = kind;
    this.stderr = stderr;
  }
}

export function defaultPython(): Promise<string> {
  return invoke<string>("default_python");
}

/**
 * Run one job and resolve with its result line (without `type`). Rejects
 * with WorkerError: kind `SpawnError` when the interpreter cannot start,
 * `WorkerCrash` when the process ends without an end line (e.g. tabgen not
 * installed in that interpreter), else the worker's own error kind.
 */
export async function runWorker<T = Record<string, unknown>>(
  python: string,
  cmd: WorkerCmd,
  args: Record<string, unknown> = {},
  onProgress?: (stage: string, pct: number) => void,
): Promise<T> {
  let end: ResultMessage | ErrorMessage | null = null;
  let badLine: string | null = null;
  const onLine = new Channel<string>();
  onLine.onmessage = (line) => {
    let message: WorkerMessage;
    try {
      message = JSON.parse(line) as WorkerMessage;
    } catch {
      badLine ??= line;
      return;
    }
    if (message.type === "progress") onProgress?.(message.stage, message.pct);
    else end = message;
  };

  let exit: WorkerExit;
  try {
    exit = await invoke<WorkerExit>("run_worker", {
      python,
      request: { cmd, args },
      onLine,
    });
  } catch (err) {
    throw new WorkerError("SpawnError", String(err));
  }

  const last = end as ResultMessage | ErrorMessage | null;
  if (last?.type === "result" && exit.code === 0) {
    const { type: _type, ...payload } = last;
    return payload as T;
  }
  if (last?.type === "error") {
    throw new WorkerError(last.kind, last.message, exit.stderr_tail);
  }
  const detail = badLine ? `unexpected output: ${badLine}` : `exit code ${exit.code}`;
  throw new WorkerError(
    "WorkerCrash",
    `the worker ended without a result (${detail})`,
    exit.stderr_tail,
  );
}
