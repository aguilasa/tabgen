---
id: FIX-UI-004
---

# FIX-UI-004 — Versionar probe e2e do pipeline frio/quente usado pela UI

Origin: [UI-TASK-04](/docs/rite/cycles/interface-desktop/04-implementar-workspace-com-progresso-por-estagio.md)

## Problem

<!-- What is wrong, stated as an observable fact. -->

Os números e2e da UI-TASK-04 (frio "Concluído 14,3 s", quente "Concluído (cache) 0,2 s", critério <5 s) vieram do cronômetro da UI e de screenshots, sem comando versionado reproduzível a partir do HEAD — a regra promovida no CLAUDE.md exige `scripts/probe_e2e_*.py` sobre amostra gerada.

## Evidência

<!-- The exact command and its output that shows the problem. Whoever fixes this reproduces it first. -->

```text
$ ls scripts/probe_e2e_*.py
scripts/probe_e2e_export.py  scripts/probe_e2e_riley.py  scripts/probe_e2e_sample.py
$ # nenhum cobre o caminho da UI: requisição `tablature` ao worker, fria e depois quente
```

## Root cause

## Fix

<!-- Where the change goes. If the defect is in generated output, the fix goes in the generator. -->

Novo `scripts/probe_e2e_worker.py`: gera a amostra senoidal de 10 s em diretório temporário novo, envia `{"cmd":"tablature","args":{"input":…}}` a `python -m tabgen.worker` duas vezes, checa que só sai NDJSON, que a ordem dos `stage` segue `_tablature_stages` + `export`, que a segunda execução tem `cache_hit: true` e roda em <5 s; imprime os tempos e PASS/FAIL.

## Arquivos

- `scripts/probe_e2e_worker.py`

## Verificação

<!-- Command(s) that turn red before the fix and green after it. -->

`.venv/bin/python scripts/probe_e2e_worker.py` → PASS com tempo frio e quente impressos; quente < 5 s.

## Execution Log
