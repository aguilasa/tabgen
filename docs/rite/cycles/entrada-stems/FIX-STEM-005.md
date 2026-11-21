---
id: FIX-STEM-005
---

# FIX-STEM-005 — Recusar --no-separate junto com --stem do mesmo instrumento

Origin: [STEM-TASK-02](/docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md)

## Problem

A decisão 2 define `--no-separate` como açúcar para `--stem <inst>=<entrada>`. Com as duas flags
juntas, `_user_stems` usa `setdefault`: o `--stem` vence e o `--no-separate` é ignorado sem aviso.

## Evidência

```text
$ .venv/bin/python -c "from pathlib import Path; from tabgen.cli.main import _user_stems; print(_user_stems(['guitar=README.md'], True, Path('pyproject.toml'), ('guitar',)))"
{'guitar': PosixPath('README.md')}
```

## Root cause

`result.setdefault(instruments[0], audio)` em `_user_stems` (`tabgen/cli/main.py`).

## Fix

Se `no_separate` estiver ligado e o instrumento já tiver `--stem`, chamar `invalid(...)` (exit 2). Caso novo em `tests/test_cli_stems.py`.

## Arquivos

- tabgen/cli/main.py
- tests/test_cli_stems.py

## Verificação

O comando da Evidência termina com `typer.Exit` (código 2) em vez de imprimir o dicionário;
`.venv/bin/pytest -q tests/test_cli_stems.py` passa com o caso novo.

Resultado (2026-11-21):
- O comando da Evidência agora termina com `typer.exceptions.Exit: 2`; antes imprimia
  `{'guitar': PosixPath('README.md')}`. O `echo $?` do pipe dá 0 por causa do `tail`.
- Na CLI, o erro sai como "Invalid option: --no-separate and --stem guitar=... both name the guitar
  stem; use one of them", com exit 2.
- `.venv/bin/pytest -q tests/test_cli_stems.py` → `10 passed`, com o caso novo no parametrize.
- `make test` → `284 passed`; `make lint` ok.

## Execution Log
