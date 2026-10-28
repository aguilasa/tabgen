import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { defaultPython, runWorker, WorkerError } from "./lib/worker";
import { loadPrefs, savePrefs, type Prefs } from "./lib/prefs";
import Ambiente from "./screens/Ambiente";

export interface DoctorCheck {
  name: string;
  ok: boolean;
  essential: boolean;
  detail: string;
  data: Record<string, unknown>;
}

export interface DoctorReport {
  ok: boolean;
  checks: DoctorCheck[];
}

export type DoctorState =
  | { state: "loading" }
  | { state: "ok" | "bad"; report: DoctorReport }
  | { state: "error"; error: WorkerError };

function badgeText(doctor: DoctorState): string {
  switch (doctor.state) {
    case "loading":
      return "Verificando ambiente…";
    case "error":
      return "Ambiente com falha · Python";
    case "bad": {
      const failed = doctor.report.checks.filter((c) => !c.ok && c.essential);
      return `Ambiente com falha · ${failed.map((c) => c.name).join(", ")}`;
    }
    case "ok": {
      const torch = doctor.report.checks.find((c) => c.name === "torch+cuda");
      const gpu = torch?.data.gpu_name;
      if (torch?.data.cuda_available && typeof gpu === "string") {
        return `Ambiente ok · ${gpu.replace(/^NVIDIA (GeForce )?/, "")} · cuda`;
      }
      return "Ambiente ok · cpu";
    }
  }
}

type Theme = "system" | "light" | "dark";

export default function App() {
  const [prefs, setPrefs] = useState<Prefs>(loadPrefs);
  const [fallbackPython, setFallbackPython] = useState("");
  const [doctor, setDoctor] = useState<DoctorState>({ state: "loading" });
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    defaultPython().then(setFallbackPython, () => setFallbackPython(""));
  }, []);

  const python = prefs.pythonPath || fallbackPython;

  const recheck = useCallback(() => {
    if (!python) return;
    setDoctor({ state: "loading" });
    runWorker<DoctorReport>(python, "doctor").then(
      (report) => setDoctor({ state: report.ok ? "ok" : "bad", report }),
      (err: unknown) =>
        setDoctor({
          state: "error",
          error: err instanceof WorkerError ? err : new WorkerError("Error", String(err)),
        }),
    );
  }, [python]);

  useEffect(recheck, [recheck]);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
  }, [theme]);

  const updatePrefs = (next: Prefs) => {
    setPrefs(next);
    savePrefs(next);
  };

  const nextTheme: Record<Theme, Theme> = { system: "dark", dark: "light", light: "system" };
  const healthy = doctor.state === "ok";

  return (
    <div className="wrap">
      <header className="titlebar">
        <span className="brand">
          tabgen <small>Studio</small>
        </span>
        <span className="spacer" />
        <span
          className={`envbadge ${healthy ? "" : doctor.state === "loading" ? "pending" : "bad"}`}
          data-testid="env-badge"
        >
          <span className="led" />
          <span>{badgeText(doctor)}</span>
        </span>
        <button type="button" className="themebtn" onClick={() => setTheme(nextTheme[theme])}>
          tema: {theme === "system" ? "sistema" : theme === "dark" ? "escuro" : "claro"}
        </button>
      </header>

      <Ambiente
        doctor={doctor}
        prefs={prefs}
        defaultPython={fallbackPython}
        onPrefsChange={updatePrefs}
        onRecheck={recheck}
      />
    </div>
  );
}
