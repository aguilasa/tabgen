// UI defaults, persisted in the webview's localStorage.

export type Device = "auto" | "cuda" | "cpu";
export type Transcriber = "riley" | "basic-pitch";

export interface Prefs {
  /** Interpreter that runs `-m tabgen.worker`; "" = the repository's .venv. */
  pythonPath: string;
  device: Device;
  transcriber: Transcriber;
  /** Output folder; "" = next to the audio file. */
  outputDir: string;
}

export const DEFAULT_PREFS: Prefs = {
  pythonPath: "",
  device: "auto",
  transcriber: "riley",
  outputDir: "",
};

const KEY = "tabgen.prefs";

export function loadPrefs(): Prefs {
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) ?? "{}") as Partial<Prefs>;
    return { ...DEFAULT_PREFS, ...stored };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

export function savePrefs(prefs: Prefs): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(prefs));
  } catch {
    // storage unavailable: the prefs stay for this session only
  }
}

/** Worker `device` arg: "auto" lets the core pick. */
export function deviceArg(device: Device): string | undefined {
  return device === "auto" ? undefined : device;
}
