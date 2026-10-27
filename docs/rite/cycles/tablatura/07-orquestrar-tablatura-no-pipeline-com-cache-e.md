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

- [ ] `.venv/bin/tabgen export <amostra>.mp3 -o out.gp5` sai 0 e `guitarpro.parse("out.gp5")`
      tem faixas guitarra e baixo com ≥1 nota.
- [ ] `-o out.musicxml` e `-o out.txt` (ou `--format`) geram MusicXML que o music21 reabre e ASCII
      não vazio.
- [ ] Segunda execução imprime `cache hit` e não chama Demucs, Basic Pitch, madmom nem a DP (teste
      com funções injetadas que falham se chamadas; medida real <5 s).
- [ ] Teste de callbacks confirma eventos `quantization`, `fretting:<instrumento>` e
      `export` chegando a 100.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

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

## Execution Log
