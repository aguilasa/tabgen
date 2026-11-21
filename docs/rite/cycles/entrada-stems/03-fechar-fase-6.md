---
id: STEM-TASK-03
---

# STEM-TASK-03 — Fechar Fase 6

## Goal

Fecha a Fase 6 (entrada de stems): os gates passam no HEAD e as checagens da fase, no profile, foram
conferidas.

## Escopo

- In:
  - Rodar os gates e as checagens da Fase 6 do profile `entrada-stems`.
  - Registrar os números no Execution Log.
- Out:
  - Código novo. O que falhar vira fix.

## Done criteria

- [ ] `make test` e `make lint` saem 0 no HEAD.
- [ ] `.venv/bin/python scripts/probe_e2e_stems.py` sai 0 com `demucs_loaded=False`.
- [ ] Export real de um stem do Moises (`~/Documents/diversos/musica/you-and-i/you-and-i-lead-gb-major-139bpm-443hz.wav`,
      copiado para o scratchpad) com `--no-separate --instruments guitar`:
  - sai 0;
  - o `.gp5` reabre com `guitarpro.parse`;
  - o tempo de separação no log de progresso é ≈0.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` vazio.

## Execution Log
