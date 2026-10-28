import Pipeline from "../components/Pipeline";
import { formatAudio, formatDuration, type RecentEntry } from "../lib/recents";
import type { RunState } from "../lib/run";

interface Props {
  song: RecentEntry;
  /** The workspace's job, whatever song it belongs to (one job at a time). */
  run: RunState | null;
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
  transcriber,
  blocked,
  onGenerate,
  onCancel,
  onBack,
}: Props) {
  const busy = run !== null && (run.phase === "running" || run.phase === "cancelling");
  const own = run?.path === song.path ? run : null;
  const otherBusy = busy && !own;
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

      <Pipeline run={own} transcriber={transcriber} onCancel={onCancel} />

      {!own && (
        <p className="muted runhint">
          {song.processed_at
            ? "Música já processada: gerar de novo reaproveita o cache dos estágios."
            : "Esta música ainda não foi processada."}
        </p>
      )}
    </section>
  );
}
