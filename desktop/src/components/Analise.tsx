import { useState } from "react";
import type { AnalysisPayload, Loadable, TablatureResult } from "../lib/run";
import { LoadablePane, NOT_RUN } from "./Stems";

/** Harte label of "no chord" (core contract, ChordSegment.label). */
const NO_CHORD = "N";

function num(value: number, digits = 1): string {
  return value.toLocaleString("pt-BR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

/** Seconds as m:ss.s. */
export function clock(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds - minutes * 60;
  return `${minutes}:${rest < 10 ? "0" : ""}${num(rest)}`;
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

interface Props {
  /** Key cross-check of the tablature run, or null when it has not run. */
  result: Pick<TablatureResult, "key_check"> | null;
  analysis: Loadable<AnalysisPayload> | null;
}

/** Análise tab: key (+ switched warning), BPM, beats, downbeats and chords. */
export default function Analise({ result, analysis }: Props) {
  const [hideNoChord, setHideNoChord] = useState(true);
  if (!result) return NOT_RUN;
  const keyCheck = result.key_check;
  const switched = keyCheck.switched === true;
  const madmomKey = typeof keyCheck.madmom_key === "string" ? keyCheck.madmom_key : "";
  const histogramKey =
    typeof keyCheck.histogram_key === "string" ? keyCheck.histogram_key : "";
  const data = analysis?.state === "ok" ? analysis.data.result : null;
  const chords = data?.chords ?? [];
  const noChord = chords.filter((c) => c.label === NO_CHORD).length;
  const shown = hideNoChord ? chords.filter((c) => c.label !== NO_CHORD) : chords;

  return (
    <div className="pane" data-testid="pane-analise">
      <div className="statrow">
        <div className="stat" data-testid="stat-key">
          <span className="k">Tom</span>
          <span className="v">{keyCheck.key || "—"}</span>
          {typeof keyCheck.key_confidence === "number" && (
            <span className="d">confiança {percent(keyCheck.key_confidence)}</span>
          )}
        </div>
        <div className="stat" data-testid="stat-bpm">
          <span className="k">BPM</span>
          <span className="v">{data ? num(data.tempo_bpm) : "…"}</span>
        </div>
        <div className="stat" data-testid="stat-beats">
          <span className="k">Beats</span>
          <span className="v">{data ? data.beat_times.length : "…"}</span>
        </div>
        <div className="stat" data-testid="stat-measures">
          <span className="k">Compassos</span>
          <span className="v">{data ? data.downbeat_times.length : "…"}</span>
          <span className="d">um por downbeat</span>
        </div>
      </div>

      {switched && (
        <div className="warnbox" data-testid="key-switched">
          <strong>Tom trocado na checagem.</strong> O madmom indicou{" "}
          <code>{madmomKey || "—"}</code>, mas o histograma das notas transcritas aponta{" "}
          <code>{histogramKey || keyCheck.key || "—"}</code>; a tablatura usa o tom do
          histograma. Vale conferir de ouvido.
        </div>
      )}

      {analysis && analysis.state !== "ok" ? (
        <LoadablePane value={analysis} what="a análise" />
      ) : (
        data && (
          <>
            <div className="panehead">
              <h3>Acordes</h3>
              <span className="spacer" />
              <label className="check-inline">
                <input
                  type="checkbox"
                  checked={hideNoChord}
                  data-testid="hide-no-chord"
                  onChange={(e) => setHideNoChord(e.target.checked)}
                />
                ocultar trechos sem acorde (N) · {noChord}
              </label>
            </div>
            {shown.length === 0 ? (
              <p className="muted empty">
                {chords.length === 0
                  ? "Nenhum acorde detectado."
                  : "Todos os trechos estão sem acorde (N)."}
              </p>
            ) : (
              <div className="tablewrap">
                <table className="chords" data-testid="chord-table">
                  <thead>
                    <tr>
                      <th>início</th>
                      <th>fim</th>
                      <th>acorde</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shown.map((c) => (
                      <tr key={`${c.start_s}-${c.label}`} className={c.label === NO_CHORD ? "nc" : ""}>
                        <td>{clock(c.start_s)}</td>
                        <td>{clock(c.end_s)}</td>
                        <td>{c.label}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )
      )}
    </div>
  );
}
