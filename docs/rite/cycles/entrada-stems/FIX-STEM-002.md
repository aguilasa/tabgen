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

## Execution Log
