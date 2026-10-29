import type { ExportFormat, ExportState, TablatureResult, TrackSummary } from "../lib/run";
import { INSTRUMENT_LABEL } from "./Notas";
import { NOT_RUN, OpenFolder } from "./Stems";

const TECHNIQUE_LABEL: Record<string, string> = {
  bend: "bend",
  slide: "slide",
  hammer_on: "hammer-on",
  pull_off: "pull-off",
};

/** Guitar types of the core (models.GUITAR_TYPES); others shown as they come. */
const TYPE_LABEL: Record<string, string> = {
  electric: "elétrica",
  nylon: "nylon",
  steel: "aço",
};

const EXPORTS: { format: ExportFormat; label: string }[] = [
  { format: "gp5", label: "Guitar Pro (.gp5)" },
  { format: "musicxml", label: "MusicXML" },
  { format: "ascii", label: "ASCII (.txt)" },
];

function seconds(ms: number): string {
  return `${(ms / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 })} s`;
}

function techniquesText(track: TrackSummary): string {
  const used = Object.entries(track.techniques).filter(([, n]) => n > 0);
  if (used.length === 0) return "nenhuma";
  return used.map(([kind, n]) => `${TECHNIQUE_LABEL[kind] ?? kind} ${n}`).join(" · ");
}

function Track({ track }: { track: TrackSummary }) {
  const name = INSTRUMENT_LABEL[track.instrument] ?? track.instrument;
  return (
    <div className="track-card" data-instrument={track.instrument}>
      <h3>
        {name}
        {track.instrument_type && (
          <small> · {TYPE_LABEL[track.instrument_type] ?? track.instrument_type}</small>
        )}
      </h3>
      <dl>
        <dt>notas</dt>
        <dd>{track.note_count}</dd>
        <dt>afinação</dt>
        <dd>
          {track.tuning_name || "personalizada"}{" "}
          <span className="mono muted">{track.tuning_notes.join(" ")}</span>
        </dd>
        <dt>capo</dt>
        <dd>{track.capo_fret > 0 ? `casa ${track.capo_fret}` : "sem capo"}</dd>
        <dt>não atribuídas</dt>
        <dd className={track.unassigned > 0 ? "warn" : ""}>{track.unassigned}</dd>
        <dt>técnicas</dt>
        <dd>{techniquesText(track)}</dd>
      </dl>
    </div>
  );
}

interface Props {
  result: TablatureResult | null;
  exporting: ExportState | null;
  onExport: (format: ExportFormat) => void;
}

/** Tablatura tab: per-track summary, the worker's ASCII preview, exports. */
export default function Tablatura({ result, exporting, onExport }: Props) {
  if (!result) return NOT_RUN;
  const busy = exporting?.phase === "running";
  return (
    <div className="pane" data-testid="pane-tablatura">
      <div className="tracks">
        {(result.tracks ?? []).map((track) => (
          <Track key={track.instrument} track={track} />
        ))}
      </div>

      <div className="panehead">
        <h3>Prévia ASCII</h3>
        <span className="spacer" />
        <span className="muted small">
          gravada em <code>{result.output_path}</code> ({result.format})
        </span>
      </div>
      <pre className="tabpre" data-testid="ascii-preview">
        {result.ascii_preview}
      </pre>
      <p className="legend">
        Prévia gerada pelo core: <code>7b9</code> bend · <code>/</code> <code>\</code> slide ·{" "}
        <code>h</code> hammer-on · <code>p</code> pull-off · <code>|</code> barra de compasso.
      </p>

      <div className="exports" data-testid="exports">
        <span className="k">Exportar</span>
        {EXPORTS.map(({ format, label }) => (
          <button
            type="button"
            key={format}
            className="btn btn-ghost btn-sm"
            data-testid={`export-${format}`}
            disabled={busy}
            onClick={() => onExport(format)}
          >
            {label}
          </button>
        ))}
      </div>
      {exporting && (
        <p
          className={`runmsg ${exporting.phase === "error" ? "err" : "ok"}`}
          data-testid="export-status"
          data-phase={exporting.phase}
        >
          {exporting.phase === "running" && `Exportando ${exporting.format}…`}
          {exporting.phase === "done" && (
            <>
              {exporting.format} gravado em <code>{exporting.outputPath}</code>
              {exporting.cacheHit ? " (tablatura do cache" : " (tablatura recalculada"}
              {exporting.endedAt !== null &&
                `, ${seconds(exporting.endedAt - exporting.startedAt)})`}{" "}
              <OpenFolder path={exporting.outputPath} />
            </>
          )}
          {exporting.phase === "error" && `Falha ao exportar ${exporting.format}: ${exporting.error}`}
        </p>
      )}
    </div>
  );
}
