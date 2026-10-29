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

- 2026-10-29 — Triagem inline (`rite reproduce --all --cycle interface-desktop`): REPRODUCED.
  `grep -c musicxml scripts/probe_e2e_worker.py` → `0` (exit 1), igual à Evidência: probe não
  cobre o export MusicXML do cache.
- 2026-10-29 — Fix (agente executor): cenário MusicXML inserido como run 3 do probe (agora 6
  runs), logo após o warm run, mesmos args mudando só `output` para `.musicxml` — formato de
  saída não entra na chave do cache de tablatura, então `cache_hit: true` vale. Asserções:
  cache_hit true, <5 s, arquivo escrito, `music21.converter.parse` com exatamente 2 partes.
  Verificação na árvore do commit: `.venv/bin/python scripts/probe_e2e_worker.py` → exit 0,
  `musicxml export OK in 0.36 s (2 parts reopened via music21.converter.parse)`; linha PASS:
  `... musicxml export from the same cache: cache_hit=true in 0.36 s (< 5 s), reopened by
  music21 with 2 parts ...`; `grep -c musicxml scripts/probe_e2e_worker.py` → 21;
  `rite gates --id FIX-UI-007` → passed (0 gates). Agente mediu na mesma árvore
  `.venv/bin/pytest -q` → 260 passed e `.venv/bin/ruff check .` → All checks passed.
