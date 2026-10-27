---
id: TAB-TASK-07
---

# TAB-TASK-07 — Orquestrar tablatura no pipeline com cache e comando export

## Goal

O estágio de tablatura está ligado ao pipeline: `run_tablature()` em `tabgen/core/pipeline.py`
reusa separação, transcrição e análise (com cache), valida o tom (TASK-04), quantiza (TASK-02),
atribui corda/casa (TASK-03) para guitarra e baixo, cacheia as `TabScore` em `.tabgen/` e exporta.
`tabgen export musica.mp3 -o musica.gp5` gera a tablatura; formato pelo sufixo de `-o` ou
`--format gp5|musicxml|ascii`; `--tuning`/`--capo` configuráveis.

## Escopo

- In: `run_tablature` com injeção das funções de estágio (padrão `run_analysis`); cache estágio
  `tablature` com versão incluindo formato do contrato e parâmetros (afinação, capo); subcomando
  `export` com barra de progresso (rich); escolha de instrumento por flag (plano, seção 7).
- Out: técnicas e afinações alternativas além de presets (Fase 4); web/desktop (Fase 5).

## Done criteria

- [x] `.venv/bin/tabgen export <amostra>.mp3 -o out.gp5` sai 0 e `guitarpro.parse("out.gp5")`
      tem faixas guitarra e baixo com ≥1 nota.
- [x] `-o out.musicxml` e `-o out.txt` (ou `--format`) geram MusicXML que o music21 reabre e ASCII
      não vazio.
- [x] Segunda execução imprime `cache hit` e não chama Demucs, Basic Pitch, madmom nem a DP (teste
      com funções injetadas que falham se chamadas; medida real <5 s).
- [x] Teste de callbacks confirma eventos `quantization`, `fretting:<instrumento>` e
      `export` chegando a 100.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Hot files: `tabgen/core/pipeline.py`, `tabgen/cli/main.py`. Pitfall herdado: conferir `files`
contra o diff nos dois sentidos antes do `rite finish`.

Encaminhado pelas TASK-05/06 (2026-10-27): os três exporters têm assinatura uniforme —
`export_gp5(scores, output_path, beat_grids=None, default_subdivisions_in_beat=4, title="")`,
`export_musicxml(scores, output_path, beat_grids=None, default_subdivisions_in_beat=4, title="")`,
`export_ascii_tab(scores, output_path, beat_grids=None, default_subdivisions_in_beat=4, measures_per_line=4)`.
`beat_grids` = por score, lista de `subdivisions_in_beat` (4 reto / 3 tercina) **paralela aos
`events` que sobrevivem ao fretting** (descartar entradas das notas em `unassigned`). Todas as
`TabScore` devem compartilhar a mesma `time_signature` (senão `Gp5ExportError` /
`MusicXmlExportError`).

Decisões de implementação:

- `run_tablature(input, output_path, fmt, instruments, tunings, capos, ...)` em
  `tabgen/core/pipeline.py`; injeção de `separate_fn`, `transcribe_fn`, `analysis_fn`
  (padrão: `run_analysis`) e `fretting_fn`. Cache estágio `tablature`, versão
  `tablature_version()` = `TAB_FORMAT_VERSION` + `TABLATURE_PIPELINE_REVISION` +
  `analysis_version()` + versão do Basic Pitch + digest sha256 dos `FrettingConfig` por
  instrumento (afinação, capo, pesos). Payload: `scores`, `beat_grids`, `key_check`,
  `unassigned`. Export não é cacheado (barato) e sempre roda.
- Tom das `TabScore` = `check_key(...).key` (TASK-04); fórmula de compasso
  `[beats_per_measure, 4]` com `beats_per_measure` inferido dos downbeats
  (`quantize._infer_beats_per_measure`, mesmo valor passado ao `quantize_notes`).
- Acordes → compassos: início de cada segmento quantizado na mesma grade das notas; só
  mudanças são anotadas, `N` nunca, primeira mudança do compasso vence.
- CLI: `tabgen export AUDIO [-o FILE] [--format gp5|musicxml|ascii] [--instruments guitar,bass]
  [--tuning PRESET|NOTAS] [--bass-tuning ...] [--capo N] [--device ...]`; formato pelo sufixo
  (`.gp5`, `.musicxml`/`.xml`, `.txt`) ou `--format`; presets em `TUNING_PRESETS`
  (guitarra: standard, drop-d, half-step-down, d-standard; baixo: standard, drop-d,
  half-step-down). Capo aplicado só à guitarra.

Resultado negativo (corrigido neste item): o primeiro e2e real gerou um `.gp5` que o
`guitarpro.parse` não reabria — `GPException: reading track 1, measure 3, voice 1, beat 11,
got ValueError: count must be less than or equal to 255`. Causa: notas com onsets a mais de
30 ms (janela de acorde da DP) caíam na mesma célula quantizada; a DP as tratava como frames
distintos e punha duas na mesma corda (ex.: corda 5, casas 4 e 1 no mesmo beat), e o beat GP5
com corda repetida corrompe o stream. Correção: `_fretting_input` dá a notas do mesmo onset
quantizado um `start_s` canônico (viram um frame da DP, cordas distintas) e deduplica altura
repetida na célula. Teste `test_notes_quantized_to_one_onset_are_fretted_as_one_chord`; controle:
sem o agrupamento ele falha com `assert 3 == 2`.

Encaminhado para a revisão da TASK-05: `export_gp5` não se protege contra duas notas na mesma
corda num beat (grava arquivo ilegível em vez de levantar `Gp5ExportError`). O pipeline não
gera mais esse caso, mas o writer deveria validar.

Verificação (2026-10-27, `You and I.flac` 4:08, caches de separação/análise/transcrição
quentes; scratchpad da sessão):

- `/usr/bin/time -f "elapsed=%es" .venv/bin/tabgen export "You and I.flac" -o out.gp5` → exit 0,
  `guitar: 2167 notes ... 25 unplayable note(s) left out`, `bass: 854 notes ... 4 unplayable`,
  `elapsed=0.58s` (estágio tablatura frio).
- `guitarpro.parse("out.gp5")` → `track guitar strings 6 notes 2225 measures 147`,
  `track bass strings 4 notes 887 measures 147`, `measures not summing to time signature: 0`.
- `-o out.musicxml` → exit 0; `music21.converter.parse` → `parts 2 measures 147 notes 2306`.
- `--format ascii -o out.txt` → exit 0; `ascii bytes 83319`, cabeçalho
  `Tuning: E2 A2 D3 G3 B3 E4 (low to high) | BPM: 139.535 | Key: F# major | Time: 4/4`.
- 2ª execução → `cache hit: tablature reused, Demucs, Basic Pitch, madmom and fretting skipped.`,
  `elapsed=0.35s`; teste `test_second_run_is_served_from_cache_without_any_stage` (funções
  injetadas que falham se chamadas) passa; controle com `StageCache.get` sempre `None` falha
  com `AssertionError: madmom must not run on a tablature cache hit`.
- `test_progress_reaches_100_for_quantization_fretting_and_export` passa.
- `.venv/bin/pytest -q` → `127 passed`; `.venv/bin/ruff check .` → `All checks passed!`;
  `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1).

## Execution Log

- **Closed** — commit `e07b62d` (2026-10-27): feat(pipeline): orchestrate tablature with caching and add export command
  - Files (`git show --name-status e07b62d`):
    - `M docs/rite/cycles/tablatura/07-orquestrar-tablatura-no-pipeline-com-cache-e.md`
    - `M docs/rite/cycles/tablatura/08-fechar-fase-3.md`
    - `M tabgen/cli/main.py`
    - `M tabgen/core/pipeline.py`
    - `A tests/test_tablature_pipeline.py`
  - **Outside declared files** (`tabgen/core/pipeline.py`, `tabgen/cli/main.py`, `tests/test_tablature_pipeline.py`):
    - `docs/rite/cycles/tablatura/08-fechar-fase-3.md`
- **Reviewed** (2026-10-27) at `600abed`: FIX-TAB-005
