---
id: ANA-TASK-02
---

# ANA-TASK-02 — Estender contrato AnalysisResult com acordes e tom

## Goal

O contrato `AnalysisResult` (`tabgen/core/models.py`) carrega tudo que a Fase 2 produz:
além de BPM, beats, downbeats e tom (já existentes), uma sequência de acordes com início, fim e
rótulo, e a confiança/escala do tom — serializável em JSON só com builtins e com round-trip
testado.

## Escopo

- In: dataclass de segmento de acorde (`start`, `end`, `label`) e lista `chords` em
  `AnalysisResult`; representação do tom (tônica + modo, ex. `"A minor"`) e `from_dict` que
  reconstrói os acordes aninhados; testes de round-trip.
- Out: os processadores madmom (TASK-03/04); `tuning_offset_cents` continua existindo mas não é
  calculado nesta fase.

## Done criteria

- [ ] `.venv/bin/pytest -q tests/test_models.py` verde, com teste que faz
      `AnalysisResult.from_json(r.to_json()) == r` para um resultado com ≥2 acordes.
- [ ] `json.dumps(r.to_dict())` funciona sem encoder custom (sem numpy/torch no contrato).
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Seguir o padrão de `NoteEvents.from_dict` para listas de dataclasses aninhadas. Mudança de
contrato: qualquer cache futuro do estágio de análise deve versionar a chave (TASK-05).

Verificação (venv `.venv/`):

- `pytest -q tests/test_models.py` → `15 passed` (round-trip com 3 acordes; backward-compat:
  JSON antigo sem `chords`/`key_confidence` carrega com lista vazia / 0.0).
- `json.dumps(r.to_dict())` com 2 acordes → ok sem encoder custom; `from_json(to_json()) == r`
  → True (medido na thread principal).
- `pytest -q` → `58 passed` · `ruff check .` → limpo · grep core puro → vazio, exit 1.

Desenho: `ChordSegment(start_s, end_s, label)` — nomes seguem o padrão de `Note` (`_s`);
label estilo Harte ("A:min", "N"). `key` continua string "<tônica> <modo>" ("A minor");
novo `key_confidence: float = 0.0` ([0,1]). `chords: list[ChordSegment]` com default vazio;
`from_dict` reconstrói via padrão do `NoteEvents`. `tuning_offset_cents` intacto.
Forma do contrato mudou → cache do estágio de análise (ANA-TASK-05) deve versionar a chave.

## Execution Log

- **Closed** — commit `3cc2424` (2026-10-26): feat(core): extend AnalysisResult with chord segments and key confidence
  - Files (`git show --name-status 3cc2424`):
    - `M tabgen/core/models.py`
    - `M tests/test_models.py`
- **Reviewed** (2026-10-26) at `c252df5`: no finding
