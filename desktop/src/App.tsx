import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { defaultPython, runWorker, WorkerError } from "./lib/worker";
import { loadPrefs, savePrefs, type Prefs } from "./lib/prefs";
import {
  baseName,
  extensionOf,
  isSupportedAudio,
  loadRecents,
  markProcessed,
  probeAudio,
  pruneRecents,
  rememberRecent,
  startupOpen,
  type RecentEntry,
} from "./lib/recents";
import {
  runArtifacts,
  useExports,
  useRunDetails,
  useTablatureRun,
  type TablatureResult,
} from "./lib/run";
import Ambiente from "./screens/Ambiente";
import Inicio from "./screens/Inicio";
import Musica from "./screens/Musica";

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
type Screen = "inicio" | "musica" | "ambiente";

function refusalMessage(path: string): string {
  const ext = extensionOf(path);
  const what = ext ? `Arquivos .${ext} não são suportados` : "Esse arquivo não tem extensão";
  return `${what} (${baseName(path)}). Escolha um áudio mp3, wav ou flac — ` +
    "converta antes, por exemplo: ffmpeg -i entrada.ogg saida.wav";
}

export default function App() {
  const [prefs, setPrefs] = useState<Prefs>(loadPrefs);
  const [fallbackPython, setFallbackPython] = useState("");
  const [doctor, setDoctor] = useState<DoctorState>({ state: "loading" });
  const [theme, setTheme] = useState<Theme>("system");
  const [screen, setScreen] = useState<Screen>("inicio");
  const [song, setSong] = useState<RecentEntry | null>(null);
  const [recents, setRecents] = useState<RecentEntry[]>(loadRecents);
  const [opening, setOpening] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  /** Single entry point for the picker, drag-and-drop, recents and TABGEN_OPEN. */
  const openSong = useCallback(async (path: string) => {
    setOpenError(null);
    if (!isSupportedAudio(path)) {
      setOpenError(refusalMessage(path));
      return;
    }
    setOpening(path);
    try {
      const info = await probeAudio(path);
      const entry: RecentEntry = {
        path,
        name: baseName(path),
        ...info,
        opened_at: new Date().toISOString(),
        processed_at: null,
        artifacts: [],
      };
      const next = rememberRecent(entry);
      setRecents(next);
      setSong(next[0]);
      setScreen("musica");
    } catch (err) {
      setOpenError(`Não foi possível abrir ${baseName(path)}: ${String(err)}`);
      setRecents(await pruneRecents());
    } finally {
      setOpening(null);
    }
  }, []);

  useEffect(() => {
    startupOpen().then((path) => {
      if (path) void openSong(path);
    }, () => {});
  }, [openSong]);

  // Back on the start screen: drop recents whose file was deleted.
  useEffect(() => {
    if (screen === "inicio") pruneRecents().then(setRecents, () => {});
  }, [screen]);

  useEffect(() => {
    defaultPython().then(setFallbackPython, () => setFallbackPython(""));
  }, []);

  const python = prefs.pythonPath || fallbackPython;

  const onRunFinished = useCallback((path: string, result: TablatureResult) => {
    const next = markProcessed(path, runArtifacts(result));
    setRecents(next);
    setSong((current) =>
      current?.path === path ? (next.find((e) => e.path === path) ?? current) : current,
    );
  }, []);
  const tablature = useTablatureRun(python, prefs, onRunFinished);
  const details = useRunDetails(python, tablature.run);
  const exports = useExports(python, tablature.run);

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
        <button type="button" className="brand" onClick={() => setScreen("inicio")}>
          tabgen <small>Studio</small>
        </button>
        <span className="spacer" />
        <button
          type="button"
          className={`envbadge ${healthy ? "" : doctor.state === "loading" ? "pending" : "bad"}`}
          data-testid="env-badge"
          onClick={() => setScreen("ambiente")}
          title="Ver ambiente"
        >
          <span className="led" />
          <span>{badgeText(doctor)}</span>
        </button>
        <button type="button" className="themebtn" onClick={() => setTheme(nextTheme[theme])}>
          tema: {theme === "system" ? "sistema" : theme === "dark" ? "escuro" : "claro"}
        </button>
      </header>

      {screen === "inicio" && (
        <Inicio
          recents={recents}
          opening={opening}
          error={openError}
          onOpen={openSong}
          onDismissError={() => setOpenError(null)}
        />
      )}
      {screen === "musica" && song && (
        <Musica
          song={song}
          run={tablature.run}
          details={details}
          exporting={exports.current}
          onExport={exports.start}
          transcriber={prefs.transcriber}
          blocked={python ? null : "Interpretador Python ainda não definido"}
          onGenerate={() => tablature.start(song.path)}
          onCancel={tablature.cancel}
          onBack={() => setScreen("inicio")}
        />
      )}
      {screen === "ambiente" && (
        <>
          <button type="button" className="backlink" onClick={() => setScreen("inicio")}>
            ← Início
          </button>
          <Ambiente
            doctor={doctor}
            prefs={prefs}
            defaultPython={fallbackPython}
            onPrefsChange={updatePrefs}
            onRecheck={recheck}
          />
        </>
      )}
    </div>
  );
}
