import { useState } from "react";
import Analise from "../components/Analise";
import Notas from "../components/Notas";
import Pipeline from "../components/Pipeline";
import Stems from "../components/Stems";
import Tablatura from "../components/Tablatura";
import { formatAudio, formatDuration, type RecentEntry } from "../lib/recents";
import type { ExportFormat, ExportState, RunDetails, RunState } from "../lib/run";

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
  transcriber: string;
  /** Why "Gerar tab" cannot run now (e.g. no interpreter yet), or null. */
  blocked: string | null;
  onGenerate: () => void;
  onCancel: () => void;
  onBack: () => void;
}

/** Song workspace: header with "Gerar tab ▶", stage cards and the run panel. */
export default function Musica({
  song,
  run,
  details,
  exporting,
  onExport,
  transcriber,
  blocked,
  onGenerate,
  onCancel,
  onBack,
}: Props) {
  const [tab, setTab] = useState<Tab>("geral");
  const busy = run !== null && (run.phase === "running" || run.phase === "cancelling");
  const own = run?.path === song.path ? run : null;
  const otherBusy = busy && !own;
  const done = own?.phase === "done" ? own : null;
  const result = done?.result ?? null;
  const ownDetails = done && details?.jobId === done.jobId ? details : null;
  const title = otherBusy
    ? `Outra música está sendo processada (${run.path})`
    : (blocked ?? "Gerar a tablatura com as opções padrão");

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
            onClick={onGenerate}
            disabled={busy || blocked !== null}
            title={title}
          >
            Gerar tab ▶
          </button>
        </div>
      </div>

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
    </section>
  );
}
