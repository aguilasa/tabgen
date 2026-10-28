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

- [ ] Escolher um mp3 real abre o workspace com nome/duração corretos; o arquivo aparece em
      recentes ao voltar (screenshot nas Notes).
- [ ] Arquivo de extensão não suportada é recusado com mensagem orientando.
- [ ] Recentes sobrevivem a fechar e reabrir o app; entrada com arquivo apagado some da lista.
- [ ] `npm run build` e typecheck do frontend saem 0.

## Notes

Duração do áudio pode vir do worker (`doctor` não cobre; usar probe leve via ffprobe no worker
se precisar — decidir na execução e registrar).

## Execution Log
