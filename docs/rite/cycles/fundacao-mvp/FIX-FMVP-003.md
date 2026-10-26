---
id: FIX-FMVP-003
---

# FIX-FMVP-003 — Gates do profile (pytest, ruff) falham fora do venv do projeto

Origin: [FIX-FMVP-001](/docs/rite/cycles/fundacao-mvp/FIX-FMVP-001.md)

## Problem

Os gates do ciclo (`pytest -q`, `ruff check .`, definidos em
`docs/rite/profiles/fundacao-mvp.md § Gates`) ficam vermelhos quando `rite gates` roda sem o
venv do projeto no `PATH`: `pytest` bare resolve para o Python 3.13 do mise (sem `tabgen`,
`typer` etc. instalados) e `ruff` nem existe no PATH (`command not found`, exit 127). O mesmo
tree passa com `.venv/bin` prefixado no `PATH` (29 passed; All checks passed!). Vermelho
pré-existente, confirmado com a wave inteira em stash sobre `9f71cd9` — não introduzido pelos
fixes desta rodada.

## Evidência

```text
$ sh "$RITE_HOME/bin/rite" gates --cycle fundacao-mvp --json   # PATH sem .venv/bin
  "command": "pytest -q",  "exit_code": 2,  "passed": false
  ... E   ModuleNotFoundError: No module named 'tabgen'
  ... E   ModuleNotFoundError: No module named 'typer'
  "command": "ruff check .",  "exit_code": 127,  "passed": false
  "/usr/bin/bash: line 1: ruff: command not found"
$ PATH="$PWD/.venv/bin:$PATH" sh "$RITE_HOME/bin/rite" gates --cycle fundacao-mvp --json
  "command": "pytest -q",  "passed": true    # 29 passed, 1 warning
  "command": "ruff check .",  "passed": true # All checks passed!
```

## Root cause

Hipótese: os comandos de gate do profile foram escritos assumindo venv ativado no shell; o runner
de gates do Rite executa em bash limpo, onde `pytest`/`ruff` resolvem para fora do venv.

## Fix

Tornar os gates auto-suficientes: trocar os comandos no profile (ou em `rite.toml [gates]`) para
`.venv/bin/pytest -q` e `.venv/bin/ruff check .` — ou garantir o venv no ambiente do runner.
Decisão de configuração do usuário; não alterado nesta rodada.

## Arquivos

- `docs/rite/profiles/fundacao-mvp.md`

## Verificação

```text
$ sh "$RITE_HOME/bin/rite" gates --cycle fundacao-mvp --json
```

Hoje `"passed": false` sem venv no PATH (vermelho); depois do fix, `"passed": true` em shell
limpo (verde).

## Execution Log
