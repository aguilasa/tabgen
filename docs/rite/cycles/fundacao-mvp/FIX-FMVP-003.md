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

Medido após o fix (2026-10-26, shell sem venv no PATH):

```text
$ sh "$RITE_HOME/bin/rite" gates --cycle fundacao-mvp --json
"command": ".venv/bin/pytest -q",  "passed": true   # 29 passed, 1 warning
"command": ".venv/bin/ruff check .",  "passed": true # All checks passed!
"passed": true
```

## Notas

Causa raiz: os gates do profile usavam `pytest`/`ruff` nus, resolvidos pelo PATH; fora do venv do
projeto o pytest caía no Python 3.13 do mise (sem tabgen/typer) e o ruff nem existia (exit 127).
Correção: gates apontam para `.venv/bin/pytest` e `.venv/bin/ruff`, tornando-os autossuficientes.
Pressupõe execução a partir da raiz do repositório (caminho relativo `.venv/bin/...`), que é como
`rite gates` roda (`"where": "."`).

Encaminhamentos do sweep (fora do escopo deste fix, sem edição): `docs/rite/COMMANDS.md:116` e os
done-criteria das tasks 01, 03–08 ainda citam `pytest -q`/`ruff check .` nus (lidos como "rodar no
venv", provavelmente intencional); profile § Phase-specific checks (Fase 0) idem.

## Execution Log

- 2026-10-26 — Triagem (`rite reproduce FIX-FMVP-003`): REPRODUCED.

  ```text
  $ sh "$RITE_HOME/bin/rite" gates --cycle fundacao-mvp --json   # PATH sem .venv/bin
  "command": "pytest -q", "exit_code": 2, "passed": false   # ModuleNotFoundError: tabgen / typer
  "command": "ruff check .", "exit_code": 127, "passed": false  # ruff: command not found
  "passed": false
  $ PATH="$PWD/.venv/bin:$PATH" sh "$RITE_HOME/bin/rite" gates --cycle fundacao-mvp --json
  "passed": true   # pytest: 29 passed, 1 warning; ruff: All checks passed!
  ```
- **Closed** — commit `5e90a46` (2026-10-26): fix(rite): use .venv binaries in cycle gates so they pass without venv on PATH
  - Files (`git show --name-status 5e90a46`):
    - `M docs/rite/profiles/fundacao-mvp.md`
