import type { Loadable, TranscriptionPayload } from "../lib/run";
import { LoadablePane, NOT_RUN, OpenFolder } from "./Stems";

export const INSTRUMENT_LABEL: Record<string, string> = {
  guitar: "guitarra",
  bass: "baixo",
};

interface Props {
  /** `transcribe` of the finished run (it writes the .mid files), or null. */
  transcription: Loadable<TranscriptionPayload> | null;
}

/** Notas tab: per instrument, note count, transcriber and the .mid path. */
export default function Notas({ transcription }: Props) {
  if (!transcription) return NOT_RUN;
  if (transcription.state !== "ok") {
    return <LoadablePane value={transcription} what="as notas" />;
  }
  const { instruments } = transcription.data;
  return (
    <div className="pane" data-testid="pane-notas">
      <div className="statrow">
        {instruments.map((item) => (
          <div className="stat" key={item.instrument} data-instrument={item.instrument}>
            <span className="k">{INSTRUMENT_LABEL[item.instrument] ?? item.instrument}</span>
            <span className="v">{item.note_count} notas</span>
            <span className="d">
              {item.transcriber}
              {item.cache_hit ? " · cache" : ""}
            </span>
          </div>
        ))}
      </div>
      <ul className="rows">
        {instruments.map((item) => (
          <li className="row" key={item.instrument}>
            <span className="rname">
              {INSTRUMENT_LABEL[item.instrument] ?? item.instrument}
            </span>
            <span className="rpath" data-testid="midi-path">
              {item.midi_path}
            </span>
            <OpenFolder path={item.midi_path} />
          </li>
        ))}
      </ul>
      <p className="legend">
        Notas transcritas antes da quantização e do dedilhado; a aba Tablatura mostra as que
        viraram casa.
      </p>
    </div>
  );
}
