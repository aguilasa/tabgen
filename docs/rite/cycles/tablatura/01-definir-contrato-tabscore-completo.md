---
id: TAB-TASK-01
---

# TAB-TASK-01 — Definir contrato TabScore completo

## Goal

O contrato `TabScore` (`tabgen/core/models.py`) deixa de ser esqueleto: tem afinação (MIDI
por corda, nº de cordas variável), capo, instrumento, BPM, armadura (tom), fórmula de compasso e
uma lista de eventos tipados — cada nota com corda, casa, posição quantizada (compasso, tempo,
subdivisão) e duração em subdivisões, além dos tempos em segundos de origem; mais os acordes
anotados por compasso. Serializável em JSON só com builtins, round-trip testado.

## Escopo

- In: dataclasses `TabNote`/`TabEvent` (nome livre) substituindo `events: list[dict]`; campos de
  cabeçalho (instrument, tuning_midi, capo_fret, tempo_bpm, key, time_signature); `from_dict` com
  listas aninhadas; presets de afinação (guitarra 6 E padrão, baixo 4 E padrão) como constantes.
- Out: algoritmos (TASK-02/03); técnicas (bend/slide/hammer — Fase 4).

## Done criteria

- [ ] `.venv/bin/pytest -q tests/test_models.py` verde, com teste `TabScore.from_json(t.to_json()) == t`
      para uma partitura de baixo (4 cordas) com ≥3 notas e ≥1 acorde anotado.
- [ ] `grep -n "events: list\[dict" tabgen/core/models.py` não retorna nada (eventos tipados).
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Contrato muda: chave de cache do estágio de tablatura deve incluir versão do formato (TASK-07).
Seguir o padrão de `AnalysisResult.from_dict`.

## Execution Log
