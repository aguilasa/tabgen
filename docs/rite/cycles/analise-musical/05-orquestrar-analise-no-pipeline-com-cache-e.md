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

- [x] `.venv/bin/tabgen analyze <amostra>.mp3` sai 0, imprime tom, BPM e sequência de acordes, e
      grava JSON que `AnalysisResult.from_json` recarrega sem erro.
- [x] Segunda execução imprime `cache hit` e não chama madmom nem Demucs (teste com funções
      injetadas que falham se chamadas; e medida real <5 s).
- [x] Teste de callbacks confirma eventos `separation`, `analysis:beats`, `analysis:harmony`
      chegando a 100.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Hot files: `tabgen/core/pipeline.py`, `tabgen/cli/main.py`. Comando da CLI segue o padrão em
inglês já usado (`separate`, `transcribe`).

Implementação: `run_analysis()` segue o padrão de injeção de `run_transcription` (`separate_fn`,
`beats_fn`, `harmony_fn`); beats roda sobre o áudio original (como em ANA-TASK-03 — o tracker de
downbeats quer a percussão) e harmonia sobre o dict de stems da separação. O resultado mesclado
(`AnalysisResult`) é cacheado no estágio `analysis` com versão `analysis_version()` =
`madmom-<versão instalada>+htdemucs_ft+htdemucs_6s+contract-2` (madmom via `importlib.metadata`,
sem importar o pacote; `contract-2` = chords + key_confidence do ANA-TASK-02; a versão do Demucs
entra porque os stems determinam a harmonia). Em cache hit de análise a separação nem é
consultada: os três estágios reportam 100 imediatamente e o `AnalysisSummary` marca
`analysis_cache_hit`. O comando `analyze` imprime tom (com confiança), BPM (com contagem de
beats/downbeats) e a sequência de acordes, grava `<input>.analysis.json` (ou `--output`) e usa a
mesma mensagem `cache hit` dos comandos existentes. Testes novos em
`tests/test_analysis_pipeline.py` (fakes injetados, cache servido sem chamar nenhum estágio,
invalidação por bytes do input, callbacks até 100). Verificação real na amostra de 10 s: primeira
execução roda madmom e detecta "D minor"/62.5 BPM; a segunda sai em ~0,2 s com `cache hit`.

## Execution Log

- **Closed** — commit `1455cf0` (2026-10-26): feat(analysis): orchestrate run_analysis with cache and analyze command
  - Files (`git show --name-status 1455cf0`):
    - `M docs/rite/cycles/analise-musical/05-orquestrar-analise-no-pipeline-com-cache-e.md`
    - `M tabgen/cli/main.py`
    - `M tabgen/core/pipeline.py`
    - `A tests/test_analysis_pipeline.py`
