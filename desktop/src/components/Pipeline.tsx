import { useEffect, useState } from "react";
import {
  cardStatus,
  STAGE_CARDS,
  type CardStatus,
  type RunPhase,
  type RunState,
  type StageProgress,
} from "../lib/run";
import { baseName } from "../lib/recents";

const PILL: Record<CardStatus, { cls: string; text: string }> = {
  pending: { cls: "off", text: "pendente" },
  cache: { cls: "cache", text: "cache" },
  running: { cls: "run", text: "rodando" },
  ok: { cls: "ok", text: "ok" },
  error: { cls: "err", text: "erro" },
  cancelled: { cls: "off", text: "cancelado" },
};

function seconds(ms: number): string {
  return `${(ms / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 })} s`;
}

function cardDetail(run: RunState | null, index: number, transcriber: string): string {
  const result = run?.result;
  if (!result) return "";
  switch (STAGE_CARDS[index].title) {
    case "Análise":
      return result.key_check.key ?? "";
    case "Transcrição":
      return transcriber;
    case "Tablatura":
      return baseName(result.output_path);
    default:
      return "";
  }
}

function useElapsed(run: RunState | null): number {
  const [now, setNow] = useState(() => performance.now());
  const live = run !== null && run.endedAt === null;
  useEffect(() => {
    if (!live) return;
    const timer = window.setInterval(() => setNow(performance.now()), 200);
    return () => window.clearInterval(timer);
  }, [live]);
  if (!run) return 0;
  return (run.endedAt ?? Math.max(now, run.startedAt)) - run.startedAt;
}

function StageBar({ stage, phase }: { stage: StageProgress; phase: RunPhase }) {
  const done = stage.pct >= 100;
  const state = done ? "done" : phase === "error" ? "fail" : phase === "cancelled" ? "stopped" : "";
  return (
    <div className={`bar ${state}`} data-stage={stage.name}>
      <span className="lbl" title={stage.name}>
        {stage.name}
      </span>
      <span className="track">
        <span className="fill" style={{ width: `${Math.min(stage.pct, 100)}%` }} />
      </span>
      <span className="pct">{done && stage.cached ? "cache" : `${Math.round(stage.pct)}%`}</span>
    </div>
  );
}

interface Props {
  /** The run of this song, or null when it has not run in this session. */
  run: RunState | null;
  transcriber: string;
  onCancel: () => void;
}

/** Stage cards and the run panel (one bar per core stage). */
export default function Pipeline({ run, transcriber, onCancel }: Props) {
  const elapsed = useElapsed(run);
  const live = run?.phase === "running" || run?.phase === "cancelling";
  const current = run?.stages.find((s) => s.pct < 100);

  return (
    <>
      <div className="stagegrid" data-testid="stage-cards">
        {STAGE_CARDS.map((card, index) => {
          const status = cardStatus(run, index);
          const pill = PILL[status];
          const detail = cardDetail(run, index, transcriber);
          return (
            <div className="stage" key={card.title} data-status={status}>
              <div className="sname">{card.title}</div>
              <div className="sval">
                <span className={`pill ${pill.cls}`}>{pill.text}</span>
                {detail && <span className="sdetail">{detail}</span>}
              </div>
            </div>
          );
        })}
      </div>

      {run && (
        <div className="runbox" data-testid="runbox" data-phase={run.phase}>
          <h3>
            <span>
              {run.phase === "running" &&
                (current ? `Rodando: ${current.name}` : "Iniciando o worker…")}
              {run.phase === "cancelling" && "Cancelando…"}
              {run.phase === "done" &&
                (run.result?.cache_hit ? "Concluído (cache)" : "Concluído")}
              {run.phase === "error" && "Falhou"}
              {run.phase === "cancelled" && "Cancelado"}
            </span>
            <span className="elapsed" data-testid="elapsed">
              {seconds(elapsed)}
            </span>
            <span className="spacer" />
            {live && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={onCancel}
                disabled={run.phase === "cancelling"}
              >
                Cancelar
              </button>
            )}
          </h3>
          {run.stages.length > 0 && (
            <div className="bars">
              {run.stages.map((stage) => (
                <StageBar key={stage.name} stage={stage} phase={run.phase} />
              ))}
            </div>
          )}
          {run.phase === "done" && run.result && (
            <p className="runmsg ok" data-testid="run-result">
              Tablatura gravada em <code>{run.result.output_path}</code> (
              {run.result.format}
              {run.result.cache_hit ? ", do cache" : ""})
              {run.result.key_check.key ? ` · tom ${run.result.key_check.key}` : ""}
              {Object.entries(run.result.unassigned)
                .filter(([, n]) => n > 0)
                .map(([name, n]) => ` · ${name}: ${n} nota(s) sem casa`)
                .join("")}
            </p>
          )}
          {run.phase === "cancelled" && (
            <p className="runmsg" data-testid="run-cancelled">
              Cancelado: o processo do worker foi encerrado. Os estágios já concluídos ficam no
              cache e são reaproveitados na próxima execução.
            </p>
          )}
          {run.phase === "error" && run.error && (
            <div className="runmsg err" data-testid="run-error">
              <strong>{run.error.kind}</strong>: {run.error.message}
              {run.error.stderr && (
                <details>
                  <summary>stderr do worker</summary>
                  <pre>{run.error.stderr}</pre>
                </details>
              )}
            </div>
          )}
        </div>
      )}
    </>
  );
}
