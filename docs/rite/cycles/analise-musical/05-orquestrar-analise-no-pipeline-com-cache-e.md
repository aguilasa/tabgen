---
id: ANA-TASK-05
---

# ANA-TASK-05 — Orquestrar análise no pipeline com cache e comando analyze

## Goal

O estágio de análise está ligado ao pipeline: `run_analysis()` em `tabgen/core/pipeline.py`
obtém os stems (reusando o cache da separação ou rodando-a), chama beats (TASK-03) e harmonia
(TASK-04), cacheia o `AnalysisResult` em `.tabgen/` e emite progresso por estágio. `tabgen analyze
musica.mp3` imprime relatório (tom, BPM, sequência de acordes) e grava `<input>.analysis.json`.

## Escopo

- In: `run_analysis` com injeção das funções de estágio (padrão de `run_transcription`); cache
  estágio `analysis` com versão que inclua o madmom e o formato do contrato; subcomando `analyze`
  com barra de progresso (rich) e saída `--output`/padrão ao lado do input.
- Out: export para tablatura; incluir análise no `transcribe` (Fase 3).

## Done criteria

- [ ] `.venv/bin/tabgen analyze <amostra>.mp3` sai 0, imprime tom, BPM e sequência de acordes, e
      grava JSON que `AnalysisResult.from_json` recarrega sem erro.
- [ ] Segunda execução imprime `cache hit` e não chama madmom nem Demucs (teste com funções
      injetadas que falham se chamadas; e medida real <5 s).
- [ ] Teste de callbacks confirma eventos `separation`, `analysis:beats`, `analysis:harmony`
      chegando a 100.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Hot files: `tabgen/core/pipeline.py`, `tabgen/cli/main.py`. Comando da CLI segue o padrão em
inglês já usado (`separate`, `transcribe`).

## Execution Log
