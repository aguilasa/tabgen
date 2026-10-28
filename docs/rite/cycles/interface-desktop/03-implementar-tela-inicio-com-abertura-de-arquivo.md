---
id: UI-TASK-03
---

# UI-TASK-03 — Implementar tela Início com abertura de arquivo e recentes

## Goal

A tela Início existe conforme o protótipo: zona de arrastar/soltar + "Escolher arquivo…"
(mp3/wav/flac), lista de recentes persistida pela UI (arquivo, duração, quando foi processada,
badges de artefatos/cache) e navegação para o workspace da música escolhida.

## Escopo

- In: file picker nativo (dialog do Tauri) e drag-and-drop; validação de extensão; recentes no
  store da UI (caminho + metadados; remove entradas cujo arquivo sumiu); navegação.
- Out: processamento (04); biblioteca com busca (v2).

## Done criteria

- [x] Escolher um mp3 real abre o workspace com nome/duração corretos; o arquivo aparece em
      recentes ao voltar (screenshot nas Notes).
- [x] Arquivo de extensão não suportada é recusado com mensagem orientando.
- [x] Recentes sobrevivem a fechar e reabrir o app; entrada com arquivo apagado some da lista.
- [x] `npm run build` e typecheck do frontend saem 0.

## Notes

Duração do áudio pode vir do worker (`doctor` não cobre; usar probe leve via ffprobe no worker
se precisar — decidir na execução e registrar).

Implementado por rite-worker no batch com UI-TASK-04 (ondas separadas: os dois mexem em App.tsx,
lib.rs, Cargo.toml e package.json).

Decisões:

- Duração vem do comando Rust `probe_audio` (`ffprobe`, já exigido pelo tabgen e checado pelo
  doctor): trata mp3/wav/flac igual, dá formato/taxa/canais para o cabeçalho e não depende do
  asset protocol nem dos codecs GStreamer do WebKitGTK. Áudio não decodificável é recusado.
- Um só caminho de abertura (`openSong` em App.tsx) para picker (`tauri-plugin-dialog`),
  drag-and-drop (`onDragDropEvent`), clique em recente e `TABGEN_OPEN` (hook só de debug,
  `startup_open` devolve `None` em release). Navegação: marca → Início, badge → Ambiente.
- Recentes em `localStorage` (`tabgen.recents`, até 20, mais novo primeiro); poda de arquivos
  sumidos via `file_exists` sempre que a Início aparece.
- `Musica.tsx` nasce mínimo (cabeçalho + placeholder) para a UI-TASK-04 completar.

Verificação (Xvfb `:99`, nunca o display do usuário; `XDG_DATA_HOME` no scratchpad):

- `ffprobe -v error -show_entries format=duration -of csv=p=0 out/audio/wonderwall.mp3` →
  `60.024000`; workspace mostra "wonderwall.mp3 · 1:00 · MP3 · 48 kHz · estéreo"
  (`evidencias/03-musica-wonderwall.png`); ao voltar, "wonderwall.mp3 1:00 não processada sem
  cache" em recentes (`evidencias/03-inicio-recentes.png`). Picker GTK real dirigido por xdotool
  no `:99` abriu `copia.mp3` (`evidencias/03-escolher-arquivo-copia.png`).
- `notes.ogg` → "Arquivos .ogg não são suportados (notes.ogg). Escolha um áudio mp3, wav ou
  flac — converta antes, por exemplo: ffmpeg -i entrada.ogg saida.wav"
  (`evidencias/03-recusa-ogg.png`).
- Recentes lidos do sqlite do WebKit após fechar o app: `copia.mp3` e `wonderwall.mp3`; após
  `rm copia.mp3` e reabrir, só `wonderwall.mp3 60.024 None []` (`evidencias/03-recente-apagado-some.png`).
- `npm run typecheck` rc 0; `npm run build` → `✓ built`; `cargo clippy -q` sem saída;
  `.venv/bin/pytest -q` → `237 passed`; `.venv/bin/ruff check .` → `All checks passed!`.
- Não exercitado na GUI: arrastar/soltar (sem fonte de drag no Xvfb); só typecheck.

## Execution Log
