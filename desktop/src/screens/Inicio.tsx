import { useEffect, useState } from "react";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { open } from "@tauri-apps/plugin-dialog";
import {
  AUDIO_EXTENSIONS,
  formatAudio,
  formatDuration,
  formatWhen,
  type RecentEntry,
} from "../lib/recents";

interface Props {
  recents: RecentEntry[];
  /** Path being opened (probing), if any. */
  opening: string | null;
  /** Message of the last refused/failed open. */
  error: string | null;
  onOpen: (path: string) => void;
  onDismissError: () => void;
}

export default function Inicio(props: Props) {
  const { recents, opening, error, onOpen } = props;
  const [dragging, setDragging] = useState(false);

  // Tauri hands the real paths of files dropped anywhere on the window.
  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let active = true;
    getCurrentWebview()
      .onDragDropEvent((event) => {
        const payload = event.payload;
        if (payload.type === "enter" || payload.type === "over") setDragging(true);
        else if (payload.type === "leave") setDragging(false);
        else {
          setDragging(false);
          if (payload.paths.length > 0) onOpen(payload.paths[0]);
        }
      })
      .then((fn) => {
        if (active) unlisten = fn;
        else fn();
      })
      .catch(() => {});
    return () => {
      active = false;
      unlisten?.();
    };
  }, [onOpen]);

  const pick = async () => {
    const path = await open({
      title: "Escolher música",
      multiple: false,
      directory: false,
      filters: [{ name: "Áudio (mp3, wav, flac)", extensions: [...AUDIO_EXTENSIONS] }],
    });
    if (typeof path === "string") onOpen(path);
  };

  return (
    <section>
      <div className={`drop ${dragging ? "over" : ""}`} data-testid="drop-zone">
        <div className="drop-ic">♪</div>
        <h1>Abrir uma música</h1>
        <p className="muted">Arraste um arquivo de áudio para cá ou escolha no computador.</p>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void pick()}
          disabled={opening !== null}
        >
          {opening ? "Abrindo…" : "Escolher arquivo…"}
        </button>
        <p className="formats">mp3 · wav · flac</p>
      </div>

      {error && (
        <div className="errbox drop-err" role="alert">
          <span className="cn">{error}</span>
          <button type="button" className="dismiss" onClick={props.onDismissError}>
            ×
          </button>
        </div>
      )}

      <h2 className="sect">Recentes</h2>
      {recents.length === 0 ? (
        <p className="muted empty">Nenhuma música aberta ainda.</p>
      ) : (
        <ul className="recents">
          {recents.map((entry) => (
            <li key={entry.path}>
              <button
                type="button"
                className="recent"
                onClick={() => onOpen(entry.path)}
                disabled={opening !== null}
                title={entry.path}
              >
                <span className="rec-main">
                  <span className="rec-name">{entry.name}</span>
                  <span className="rec-path">{entry.path}</span>
                </span>
                <span className="rec-meta">
                  <span className="rec-dur">{formatDuration(entry.duration_s)}</span>
                  <span className="rec-fmt">{formatAudio(entry)}</span>
                </span>
                <span className="rec-when">
                  {entry.processed_at
                    ? `processada ${formatWhen(entry.processed_at)}`
                    : "não processada"}
                </span>
                <span className="rec-badges">
                  {entry.artifacts.length === 0 ? (
                    <span className="tag none">sem cache</span>
                  ) : (
                    entry.artifacts.map((a) => (
                      <span key={a} className="tag">
                        {a}
                      </span>
                    ))
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
