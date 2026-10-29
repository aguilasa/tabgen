import { useState, type ReactNode } from "react";
import type { AnalysisPayload, Loadable } from "../lib/run";
import { openFolder } from "../lib/worker";

/** Display names of the stems; unknown names are shown as they come. */
const STEM_LABEL: Record<string, string> = {
  vocals: "voz",
  drums: "bateria",
  bass: "baixo",
  other: "outros",
  guitar: "guitarra",
};

/** "abrir pasta" button: asks the shell to show the folder of `path`. */
export function OpenFolder({ path, label = "abrir pasta" }: { path: string; label?: string }) {
  const [error, setError] = useState<string | null>(null);
  return (
    <span className="openfolder">
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        data-testid="open-folder"
        title={path}
        onClick={() => {
          setError(null);
          openFolder(path).catch((err: unknown) => setError(String(err)));
        }}
      >
        {label}
      </button>
      {error && <span className="openerr">{error}</span>}
    </span>
  );
}

/** Placeholder of a tab whose stage has not run (or is still loading). */
export function EmptyPane({ children }: { children: ReactNode }) {
  return (
    <div className="placeholder pane-empty" data-testid="pane-empty">
      {children}
    </div>
  );
}

/** Loading/error placeholder of a detail job; null when it has data. */
export function LoadablePane<T>({ value, what }: { value: Loadable<T>; what: string }) {
  if (value.state === "loading") {
    return (
      <EmptyPane>
        <p className="muted">Carregando {what} do cache…</p>
      </EmptyPane>
    );
  }
  if (value.state === "error") {
    return (
      <div className="errbox pane-err" data-testid="pane-error">
        <div className="cn">
          Não foi possível carregar {what} ({value.kind})
        </div>
        <p>{value.message}</p>
      </div>
    );
  }
  return null;
}

export const NOT_RUN = (
  <EmptyPane>
    <p>Este estágio ainda não rodou nesta sessão.</p>
    <p className="muted">Use "Gerar tab ▶" para ver os resultados aqui.</p>
  </EmptyPane>
);

interface Props {
  /** `analyze` of the finished run (it carries the stems), or null. */
  analysis: Loadable<AnalysisPayload> | null;
}

/** Stems tab: the separated stems with their path and "abrir pasta". */
export default function Stems({ analysis }: Props) {
  if (!analysis) return NOT_RUN;
  if (analysis.state !== "ok") return <LoadablePane value={analysis} what="os stems" />;
  const stems = Object.entries(analysis.data.stems);
  if (stems.length === 0) {
    return (
      <EmptyPane>
        <p>Os stems desta música não estão mais no disco.</p>
        <p className="muted">
          A pasta stems/ é compartilhada pelos áudios da mesma pasta; gere a tab de novo para
          separá-los outra vez.
        </p>
      </EmptyPane>
    );
  }
  return (
    <div className="pane" data-testid="pane-stems">
      <div className="panehead">
        <h3>{stems.length} stems</h3>
        <span className="spacer" />
        <OpenFolder path={stems[0][1]} label="abrir pasta dos stems" />
      </div>
      <ul className="rows">
        {stems.map(([name, path]) => (
          <li className="row" key={name} data-stem={name}>
            <span className="rname">{STEM_LABEL[name] ?? name}</span>
            <span className="rpath">{path}</span>
            <OpenFolder path={path} />
          </li>
        ))}
      </ul>
    </div>
  );
}
