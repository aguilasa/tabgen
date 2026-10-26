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

## Execution Log
