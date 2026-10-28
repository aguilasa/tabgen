import { formatAudio, formatDuration, type RecentEntry } from "../lib/recents";

interface Props {
  song: RecentEntry;
  onBack: () => void;
}

/** Song workspace. UI-TASK-04 adds the pipeline run and the stage cards. */
export default function Musica({ song, onBack }: Props) {
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
      </div>

      <div className="placeholder">
        <p>
          {song.processed_at ? "Música já processada." : "Esta música ainda não foi processada."}
        </p>
        <p className="muted">A geração da tablatura (separação, análise, transcrição) entra aqui.</p>
      </div>
    </section>
  );
}
