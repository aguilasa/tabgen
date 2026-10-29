---
id: FIX-UI-009
---

# FIX-UI-009 — Unificar limite de capo no core (CLI e worker têm cópias)

Origin: [UI-TASK-06](/docs/rite/cycles/interface-desktop/06-implementar-painel-de-opcoes-de-geracao.md)

## Problem

O limite 0–12 do capo existe duplicado: `min=0, max=12` hardcoded no typer da CLI e
`CAPO_RANGE = (0, 12)` no worker; nenhum vem do core, contrariando a nota da própria tarefa de
que o payload de presets vem "tudo das constantes do core". A tarefa reconhece ("duas cópias do
mesmo limite") mas nada liga as duas cópias — drift silencioso se uma mudar.

## Evidência

```text
$ grep -n "CAPO_RANGE = " tabgen/worker/__init__.py
106:CAPO_RANGE = (0, 12)

$ sed -n '341,346p' tabgen/cli/main.py
    capo: int = typer.Option(
        0,
        "--capo",
        min=0,
        max=12,
        help="Guitar capo fret (frets in the tab are relative to it).",
    ),
```

## Root cause

Hipótese (não provada): a CLI ganhou os bounds antes do worker existir e a tarefa preferiu não
tocar na CLI fora do seu escopo.

## Fix

Mover a constante para `tabgen/core` (p.ex. `CAPO_RANGE` em `tabgen/core/models.py`) e
importá-la na CLI (min/max do typer) e no worker; o teste
`test_presets_come_from_the_core_constants` passa a comparar com a constante do core.

## Arquivos

- tabgen/core/models.py
- tabgen/cli/main.py
- tabgen/worker/__init__.py
- tests/test_worker.py

## Verificação

```text
$ grep -rn "max=12\|CAPO_RANGE = (0, 12)" tabgen/cli/main.py tabgen/worker/__init__.py
```

Hoje encontra as duas cópias; depois do fix sai vazio, `grep -n "CAPO_RANGE"
tabgen/core/models.py` encontra a fonte única e `.venv/bin/pytest -q tests/test_worker.py`
fica verde.

## Execution Log

- 2026-10-29 — Triagem inline (`rite reproduce --all --cycle interface-desktop`): REPRODUCED.
  `grep -n "CAPO_RANGE = " tabgen/worker/__init__.py` → `106:CAPO_RANGE = (0, 12)`;
  `sed -n '341,346p' tabgen/cli/main.py` → `min=0, max=12` hardcoded no typer. Duas cópias,
  nenhuma no core. Saída igual à Evidência.
- 2026-10-29 — Fix (agente executor): `CAPO_RANGE: tuple[int, int] = (0, 12)` criado em
  `tabgen/core/models.py` (ao lado de GUITAR_TYPES, comentário de contrato citando os dois
  consumidores); worker importa do core (mantém re-export em `tabgen.worker`); CLI usa
  `min=CAPO_RANGE[0], max=CAPO_RANGE[1]`; teste `test_presets_come_from_the_core_constants`
  importa a constante do core e compara com o payload real (sem monkeypatch). Core puro —
  nada de CLI/worker entrou em `tabgen/core`. Verificação na árvore do commit:
  `grep -rn "max=12\|CAPO_RANGE = (0, 12)" tabgen/cli/main.py tabgen/worker/__init__.py` →
  vazio (exit 1); `grep -n "CAPO_RANGE" tabgen/core/models.py` →
  `133:CAPO_RANGE: tuple[int, int] = (0, 12)`; `.venv/bin/pytest -q tests/test_worker.py` →
  39 passed; `rite gates --id FIX-UI-009` → passed (0 gates). Agente mediu na mesma árvore
  `.venv/bin/pytest -q` → 260 passed e `.venv/bin/ruff check .` → All checks passed.
  Desktop já consome `capo_range` do payload de presets do worker — sem cópia na UI.
