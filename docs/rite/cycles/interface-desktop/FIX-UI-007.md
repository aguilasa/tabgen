---
id: FIX-UI-007
---

# FIX-UI-007 — Estender probe e2e do worker ao export MusicXML do cache

Origin: [UI-TASK-05](/docs/rite/cycles/interface-desktop/05-implementar-abas-de-resultados-com-previa-ascii.md)

## Problem

<!-- What is wrong, stated as an observable fact. -->

O critério 2 da UI-TASK-05 (export MusicXML a partir do gp5 reusa o cache em <5 s e reabre no music21) foi medido por comando inline e pelo cronômetro da UI; `scripts/probe_e2e_worker.py` não cobre esse caminho, e a regra do CLAUDE.md exige probe versionado para número e2e.

## Evidência

<!-- The exact command and its output that shows the problem. Whoever fixes this reproduces it first. -->

```text
$ grep -c musicxml scripts/probe_e2e_worker.py
0
```

## Root cause

## Fix

<!-- Where the change goes. If the defect is in generated output, the fix goes in the generator. -->

Após a execução quente, o probe envia o mesmo `tablature` com `output` `.musicxml`, exige `cache_hit: true`, tempo <5 s e `music21.converter.parse` com 2 partes; imprime o tempo.

## Arquivos

- `scripts/probe_e2e_worker.py`

## Verificação

<!-- Command(s) that turn red before the fix and green after it. -->

`.venv/bin/python scripts/probe_e2e_worker.py` → PASS com o tempo do export MusicXML impresso (<5 s).

## Execution Log
