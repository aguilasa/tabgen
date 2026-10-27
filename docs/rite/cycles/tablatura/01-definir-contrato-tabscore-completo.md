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

- [x] `.venv/bin/pytest -q tests/test_models.py` verde, com teste `TabScore.from_json(t.to_json()) == t`
      para uma partitura de baixo (4 cordas) com ≥3 notas e ≥1 acorde anotado.
- [x] `grep -n "events: list\[dict" tabgen/core/models.py` não retorna nada (eventos tipados).
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Contrato muda: chave de cache do estágio de tablatura deve incluir versão do formato (TASK-07).
Seguir o padrão de `AnalysisResult.from_dict`.

Implementado: `TabNote` (string/fret, posição quantizada measure/beat/subdivision 1-based —
subdivision 0-based —, `duration_subdivisions`, `start_s`/`end_s` originais), `MeasureChord`
(measure + label Harte) e `TabScore` completo (instrument, tuning_midi low-to-high, capo_fret,
tempo_bpm, key, time_signature como `[num, den]`, events/chords tipados com `from_dict` aninhado
no padrão de `AnalysisResult`). Presets `GUITAR_STANDARD_TUNING` (40,45,50,55,59,64) e
`BASS_STANDARD_TUNING` (28,33,38,43), ordem grave→agudo documentada em comentário. Constante
`TAB_FORMAT_VERSION = 1` já definida para a chave de cache do TASK-07 (cache em si fora do escopo).
Convenção de corda: 1-based, corda 1 = mais grave (mesma ordem de `tuning_midi`).

Evidências:
- `.venv/bin/pytest -q tests/test_models.py` → `21 passed in 0.02s` (inclui
  `test_tab_score_round_trip_for_bass_with_notes_and_chord`: baixo 4 cordas, 3 notas, 2 acordes).
- `grep -n "events: list\[dict" tabgen/core/models.py` → vazio (exit 1).
- `.venv/bin/pytest -q` → `83 passed, 11 warnings in 8.39s`; `.venv/bin/ruff check .` →
  `All checks passed!`.
- Sweep manual (CLI `rite` indisponível no sandbox): grep por `TabScore/TabNote/MeasureChord` fora
  dos arquivos do item só acha menções genéricas em docs de planejamento e itens pendentes
  (TASK-05/06/07), todas compatíveis com o novo esquema — nada desatualizado.

## Execution Log
