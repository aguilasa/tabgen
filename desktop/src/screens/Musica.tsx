import { useState } from "react";
import Analise from "../components/Analise";
import Notas from "../components/Notas";
import OpcoesDrawer from "../components/OpcoesDrawer";
import Pipeline from "../components/Pipeline";
import Stems from "../components/Stems";
import Tablatura from "../components/Tablatura";
import { formatAudio, formatDuration, type RecentEntry } from "../lib/recents";
import type { Prefs } from "../lib/prefs";
import {
  CUSTOM_TUNING,
  defaultOptions,
  type ExportFormat,
  type ExportState,
  type GenerationPresets,
  type GenOptions,
  type Loadable,
  type RunDetails,
  type RunState,
  type SongMemory,
} from "../lib/run";

type Tab = "geral" | "stems" | "analise" | "notas" | "tablatura";

const TABS: { id: Tab; label: string }[] = [
  { id: "geral", label: "Visão geral" },
  { id: "stems", label: "Stems" },
  { id: "analise", label: "Análise" },
  { id: "notas", label: "Notas" },
  { id: "tablatura", label: "Tablatura" },
];

interface Props {
  song: RecentEntry;
  /** The workspace's job, whatever song it belongs to (one job at a time). */
  run: RunState | null;
  /** Stems/analysis/notes of the workspace's finished run, or null. */
  details: RunDetails | null;
  /** Latest export of the workspace's finished run, or null. */
  exporting: ExportState | null;
  onExport: (format: ExportFormat) => void;
  python: string;
  prefs: Prefs;
  /** Option values from the worker's `presets` command. */
  presets: Loadable<GenerationPresets>;
  /** Last options used for this song, null = never generated. */
  memory: SongMemory | null;
  /** Why "Gerar tab" cannot run now (e.g. no interpreter yet), or null. */
  blocked: string | null;
  onGenerate: (options: GenOptions) => void;
  onCancel: () => void;
  onBack: () => void;
}

const INSTRUMENT_NAME: Record<string, string> = { guitar: "guitarra", bass: "baixo" };

/** One line with the remembered options, e.g. "guitarra drop-d, capo 2, nylon · …". */
function optionsSummary(options: GenOptions): string {
  const parts = options.instruments.map((name) => {
    const choice = options.tuning[name];
    const tuning = choice === CUSTOM_TUNING ? (options.customTuning[name] ?? "") : choice;
    const extra = name === "guitar" ? `, capo ${options.capo}, ${options.guitarType}` : "";
    return `${INSTRUMENT_NAME[name] ?? name} ${tuning}${extra}`;
  });
  return [
    ...parts,
    options.transcriber,
    options.techniques ? "técnicas" : "sem técnicas",
    options.device,
    options.format,
  ].join(" · ");
}

/** Song workspace: header with "Gerar tab ▶", stage cards and the run panel. */
export default function Musica({
  song,
  run,
  details,
  exporting,
  onExport,
  python,
  prefs,
  presets,
  memory,
  blocked,
  onGenerate,
  onCancel,
  onBack,
}: Props) {
  const [tab, setTab] = useState<Tab>("geral");
  const [drawer, setDrawer] = useState(false);
  const busy = run !== null && (run.phase === "running" || run.phase === "cancelling");
  const own = run?.path === song.path ? run : null;
  const otherBusy = busy && !own;
  const done = own?.phase === "done" ? own : null;
  const result = done?.result ?? null;
  const ownDetails = done && details?.jobId === done.jobId ? details : null;
  const presetsError =
    presets.state === "error" ? `Opções indisponíveis (${presets.kind}: ${presets.message})` : null;
  const title = otherBusy
    ? `Outra música está sendo processada (${run.path})`
    : (blocked ?? presetsError ?? "Escolher as opções e gerar a tablatura");
  // the run's own transcriber; without a guitar part every track is basic-pitch
  const runArgs = own?.args;
  const transcriber =
    runArgs && Array.isArray(runArgs.instruments) && !runArgs.instruments.includes("guitar")
      ? "basic-pitch"
      : String(runArgs?.transcriber ?? memory?.options.transcriber ?? prefs.transcriber);
  const initial =
    presets.state === "ok"
      ? { ...defaultOptions(song.path, prefs, presets.data), ...memory?.options }
      : null;

  return (
    <section>
      <div className="songhead">
        <button type="button" className="back" onClick={onBack} title="Voltar ao início">
          ←
        </button>
        <div className="sh-main">
          <h1 data-testid="song-name">{song.name}</h1>
          <div className="sh-meta">
            <span data-testid="song-duration">{formatDuration(song.duration_s)}</span>
            <span>{formatAudio(song)}</span>
            <span className="sh-path">{song.path}</span>
          </div>
        </div>
        <div className="sh-actions">
          <button
            type="button"
            className="btn btn-primary"
            data-testid="generate"
            onClick={() => setDrawer(true)}
            disabled={busy || blocked !== null || presets.state !== "ok"}
            title={title}
          >
            Gerar tab ▶
          </button>
        </div>
      </div>
      {memory && <p className="sh-opts muted" data-testid="last-options">Últimas opções: {optionsSummary(memory.options)}</p>}

      <nav className="tabs" role="tablist">
        {TABS.map(({ id, label }) => (
          <button
            type="button"
            role="tab"
            key={id}
            className={`tab ${tab === id ? "on" : ""}`}
            aria-selected={tab === id}
            data-testid={`tab-${id}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "geral" && (
        <>
          <Pipeline run={own} transcriber={transcriber} onCancel={onCancel} />
          {!own && (
            <p className="muted runhint">
              {song.processed_at
                ? "Música já processada: gerar de novo reaproveita o cache dos estágios."
                : "Esta música ainda não foi processada."}
            </p>
          )}
        </>
      )}
      {tab === "stems" && <Stems analysis={ownDetails?.analysis ?? null} />}
      {tab === "analise" && (
        <Analise result={result} analysis={ownDetails?.analysis ?? null} />
      )}
      {tab === "notas" && <Notas transcription={ownDetails?.transcription ?? null} />}
      {tab === "tablatura" && (
        <Tablatura result={result} exporting={exporting} onExport={onExport} />
      )}
      {drawer && presets.state === "ok" && initial && (
        <OpcoesDrawer
          songName={song.name}
          durationS={song.duration_s}
          python={python}
          presets={presets.data}
          initial={initial}
          memory={memory}
          blocked={busy ? "Um job já está rodando" : blocked}
          onClose={() => setDrawer(false)}
          onGenerate={(options) => {
            setDrawer(false);
            setTab("geral");
            onGenerate(options);
          }}
        />
      )}
    </section>
  );
}
