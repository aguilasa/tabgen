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

- [x] Teste: notas da escala de Sol maior com tônica enfatizada pontuam `G major` em primeiro.
- [x] Teste: madmom `A minor` + notas de Dó maior é tratado como concordante (relativo).
- [x] Teste: madmom com confiança baixa e histograma fortemente em outro tom devolve o tom do
      histograma e marca a troca (campo/flag verificável).
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Decisão do usuário (2026-10-26): esta validação foi movida da Fase 2 para cá. O tom final
alimenta a armadura no .gp5 e no MusicXML (TASK-05/06).

Implementado em `tabgen/core/analysis/key_check.py`: função pura `check_key(madmom_key,
madmom_confidence, note_events)` que monta histograma de classes de altura ponderado por duração
(guitarra + baixo juntos), correlaciona (Pearson) com os 24 perfis Krumhansl–Kessler (vetores
hardcoded com citação) e devolve `KeyCheckResult` (dataclass só com builtins JSON: `key` final no
formato `"<tonic> <mode>"` do contrato — alimenta a armadura em TASK-05/06 —, `key_confidence`,
`agreement`, `switched`, `madmom_key`, `histogram_key`, `margin`, `reason`, `scores`).

Regra de decisão (constantes documentadas): tons iguais ou relativos (ex.: `A minor` ~ `C major`)
são concordantes e o tom do madmom é mantido; em discordância, só troca para o tom do histograma
quando `madmom_confidence < MIN_MADMOM_CONFIDENCE` (0.7) **e** a vantagem de correlação do
histograma sobre o tom do madmom (ou seu relativo) é `>= MIN_MARGIN` (0.10); troca marcada com
`switched=True` e `reason="histogram_override"`. Casos de borda: sem notas mantém madmom
(`no_notes`); madmom vazio adota o histograma (`no_madmom_key`).

Verificação executada:

- `.venv/bin/pytest tests/test_key_check.py -q` → `7 passed in 0.12s` (cobre os três critérios de
  teste: G maior em primeiro; relativo concordante; override com `switched=True`).
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1).
- `.venv/bin/ruff check .` → `All checks passed!`
- `.venv/bin/pytest -q` → `90 passed, 11 warnings in 8.41s`.

Encaminhamento: `tabgen/core/analysis/__init__.py` não exporta `key_check` (fora dos arquivos
permitidos desta tarefa); hoje ele também não reexporta `harmony`, então o padrão está coerente,
mas se um reexport for desejado, adicionar `check_key`/`KeyCheckResult` lá. Ponto de integração no
pipeline (consumir `AnalysisResult` + `NoteEvents` e usar `KeyCheckResult.key` na armadura) fica
para TASK-05/07.

## Execution Log

- **Closed** — commit `7d89f45` (2026-10-27): feat(analysis): cross-check madmom key against note histogram
  - Files (`git show --name-status 7d89f45`):
    - `M docs/rite/cycles/tablatura/04-cruzar-tom-detectado-com-histograma-de-notas.md`
    - `A tabgen/core/analysis/key_check.py`
    - `A tests/test_key_check.py`
