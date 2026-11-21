---
id: FIX-STEM-002
---

# FIX-STEM-002 — Alinhar model_version preparado ao Escopo ou registrar o desvio

Origin: [STEM-TASK-01](/docs/rite/cycles/entrada-stems/01-separacao-preparada-a-partir-de-stems-dados-no.md)

## Problem

O Escopo da STEM-TASK-01 especifica `model_version="user-stems:<hash>"`. O código devolve
`"user-stems"` (cobertura total) ou `"<demucs>+user-stems"` (parcial), e as Notes da tarefa não
registram esse desvio. Nenhuma chave de cache lê `model_version`.

## Evidência

```text
$ grep -n 'user-stems' docs/rite/cycles/entrada-stems/01-separacao-preparada-a-partir-de-stems-dados-no.md tabgen/core/separation/prepared.py
...01-...md:19:      `SeparationResult(stems=..., model_version="user-stems:<hash>")`.
tabgen/core/separation/prepared.py:20:USER_STEMS_MODEL = "user-stems"
```

## Root cause

O código seguiu a decisão 3 do plano, e não o Escopo da tarefa; a diferença não foi anotada.

## Fix

Acrescentar o digest dos stems ao `model_version` em `prepared.py` (`user-stems:<sha10>`), igual ao do `stems_tag`.

## Arquivos

- tabgen/core/separation/prepared.py
- tests/test_prepared_stems.py

## Verificação

`grep -n 'user-stems:' tabgen/core/separation/prepared.py` acha; um teste confere o `model_version` com o digest.

Resultado (2026-11-21):
- `model_version` passa a ser `user-stems:<sha10>`, o mesmo digest do `stems_tag`. No caso parcial
  fica `<demucs>+user-stems:<sha10>`.
- `.venv/bin/pytest -q tests/test_prepared_stems.py` → `14 passed`, com o teste novo
  `test_model_version_carries_the_stems_digest`.
- `grep -n 'user-stems:' tabgen/core/separation/prepared.py` acha a linha 140. É um comentário: o
  código monta o valor por f-string, e quem confere de fato é o teste.
- `make test` → `283 passed`; `make lint` ok.

## Execution Log

- **Closed** — commit `a3d554f` (2026-11-21): fix(core): include the stems digest in the prepared model_version
  - Files (`git show --name-status a3d554f`):
    - `M docs/rite/cycles/entrada-stems/FIX-STEM-002.md`
    - `M tabgen/core/separation/prepared.py`
    - `M tests/test_prepared_stems.py`
