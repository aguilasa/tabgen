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

- 2026-10-28 — Triagem inline (`rite reproduce --all --cycle interface-desktop`): REPRODUCED.
  `ls scripts/probe_e2e_*.py` → export, riley, sample — nenhum cobre o caminho da UI
  (requisição `tablature` ao worker, fria e quente). Probe inexistente no HEAD.
- 2026-10-28 — Controle antes do fix: `.venv/bin/python scripts/probe_e2e_worker.py` →
  `can't open file ... probe_e2e_worker.py: [Errno 2] No such file or directory` (exit 2).
  Adicionado `scripts/probe_e2e_worker.py`: gera a senoide de 10 s em diretório temporário
  novo (cache `.tabgen/` ao lado do input nasce frio), envia `{"cmd":"tablature",...}` a
  `python -m tabgen.worker` em dois processos (um job por processo, como a UI em
  `desktop/src/lib/worker.ts`) e afirma só os fatos estáveis: stdout 100% NDJSON, última
  linha `result`, ordem de primeira aparição dos `stage` = `_tablature_stages` + `export`
  (no frio o `separation` reaparece — `_compute_tablature` rebusca os stems já separados
  pela análise, documentado no probe), 1ª execução `cache_hit: false`, 2ª `cache_hit: true`
  e < 5 s, `.gp5` escrito. Resultado: `PASS: ... cold run cache_hit=false in 14.2 s (not
  asserted), warm run cache_hit=true in 0.17 s (< 5 s); .gp5 written.` (exit 0) — bate com
  os números da UI-TASK-04 (14,3 s / 0,2 s). Gates: `.venv/bin/pytest -q` → 237 passed
  (probe não é coletado pelo pytest); `.venv/bin/ruff check .` → All checks passed.
- 2026-10-28 — Verificação final na árvore do commit: `.venv/bin/python
  scripts/probe_e2e_worker.py` → exit 0, `PASS: ... cold run cache_hit=false in 15.0 s (not
  asserted), warm run cache_hit=true in 0.17 s (< 5 s); .gp5 written.`; `.venv/bin/pytest -q`
  → 237 passed; `.venv/bin/ruff check .` → All checks passed!; `rite gates --id FIX-UI-004`
  → passed.
- **Closed** — commit `f02c3e9` (2026-10-28): test(e2e): add worker-path cold/warm probe for the UI pipeline
  - Files (`git show --name-status f02c3e9`):
    - `M docs/rite/cycles/interface-desktop/FIX-UI-004.md`
    - `A scripts/probe_e2e_worker.py`
