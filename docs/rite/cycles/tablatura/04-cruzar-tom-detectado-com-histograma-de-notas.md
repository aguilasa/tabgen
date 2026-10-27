---
id: TAB-TASK-04
---

# TAB-TASK-04 — Cruzar tom detectado com histograma de notas transcritas

## Goal

O tom do `AnalysisResult` é validado contra o histograma de classes de altura das notas
transcritas (plano, Estágios 2–3: "validar cruzando com o histograma de notas transcritas no
estágio 4"): função pura que pontua os 24 tons (perfis Krumhansl–Kessler ou equivalente) sobre as
notas ponderadas pela duração e informa concordância ou sugere outro tom, com confiança.

## Escopo

- In: histograma ponderado por duração a partir de `NoteEvents` (guitarra + baixo); correlação com
  perfis maior/menor; regra de decisão documentada (ex.: manter madmom salvo quando o histograma
  discorda com margem e a confiança do madmom é baixa); relativos maior/menor tratados como
  compatíveis; testes sintéticos.
- Out: alterar o estágio de análise ou seu cache; transcrever (usa `NoteEvents` prontos).

## Done criteria

- [ ] Teste: notas da escala de Sol maior com tônica enfatizada pontuam `G major` em primeiro.
- [ ] Teste: madmom `A minor` + notas de Dó maior é tratado como concordante (relativo).
- [ ] Teste: madmom com confiança baixa e histograma fortemente em outro tom devolve o tom do
      histograma e marca a troca (campo/flag verificável).
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Decisão do usuário (2026-10-26): esta validação foi movida da Fase 2 para cá. O tom final
alimenta a armadura no .gp5 e no MusicXML (TASK-05/06).

## Execution Log
