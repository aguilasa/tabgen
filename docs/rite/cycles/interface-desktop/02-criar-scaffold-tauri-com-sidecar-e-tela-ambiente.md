---
id: UI-TASK-02
---

# UI-TASK-02 — Criar scaffold Tauri com sidecar e tela Ambiente

## Goal

Existe `desktop/` com app Tauri 2 + React + Vite que sobe (`npm run tauri dev`), localiza o
interpretador Python configurado (padrão: `.venv/bin/python` do repo; configurável na UI), roda o
worker como processo filho e mostra a tela Ambiente: os 5 checks do doctor com detalhe, botão
"verificar de novo", badge de resumo na barra do app e padrões persistidos (device, transcriber,
pasta de saída). Primeira fatia de ponta a ponta UI→worker→core.

## Escopo

- In: scaffold Tauri 2 (React+Vite, TypeScript); comando Rust/JS que spawna
  `python -m tabgen.worker` e entrega as linhas NDJSON ao frontend; store de preferências
  (caminho do Python, device, transcriber, pasta de saída); tela Ambiente conforme protótipo;
  tema claro/escuro do sistema.
- Out: demais telas (03–06); empacotamento (07); bundling do Python (fora da v1).

## Done criteria

- [ ] `cd desktop && npm run tauri dev` abre o app; a tela Ambiente lista os 5 checks reais com
      detalhe (GPU/VRAM, versão do madmom, disco) — screenshot nas Notes.
- [ ] Com caminho de Python inválido nas preferências, a tela mostra erro orientando e o badge
      fica vermelho (screenshot).
- [ ] `cd desktop && npm run build` sai 0; lint/typecheck do frontend (`npm run lint` ou `tsc
      --noEmit`) sai 0.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` continuam verdes (nada do Python mudou).

## Notes

Referência visual: protótipo aprovado (profile, Sources of truth). `desktop/` tem seu próprio
toolchain (npm); gates Python do repo não cobrem o frontend — checks do frontend entram nos done
criteria de cada task.

## Execution Log
