---
id: FIX-STEM-008
---

# FIX-STEM-008 — Listar o commit 5887f0d no Execution Log da STEM-TASK-03

Origin: [STEM-TASK-03](/docs/rite/cycles/entrada-stems/03-fechar-fase-6.md)

## Problem

O Execution Log da STEM-TASK-03 cita só o `d9de920`, uma correção de uma linha. O commit que marcou os
critérios e trouxe a evidência, `5887f0d` (`Refs: STEM-TASK-03`), não aparece. O `rite finish`
recusou-o por causa do prefixo `chore(rite)`, que o Rite trata como commit de registro.

## Evidência

```text
$ grep -c "5887f0d" docs/rite/cycles/entrada-stems/03-fechar-fase-6.md
0
```

## Root cause

O commit de trabalho saiu com o prefixo de commit de registro; o finish ficou com o commit seguinte.

## Fix

Acrescentar ao Execution Log uma linha para `5887f0d`, com a lista de arquivos e o motivo.

## Arquivos

- docs/rite/cycles/entrada-stems/03-fechar-fase-6.md

## Verificação

`grep -c "5887f0d" docs/rite/cycles/entrada-stems/03-fechar-fase-6.md` dá 1 ou mais.

## Execution Log

- **Closed** — commit `c3546e5` (2026-11-21): docs(rite): list 5887f0d in STEM-TASK-03 execution log
  - Files (`git show --name-status c3546e5`):
    - `M docs/rite/cycles/entrada-stems/03-fechar-fase-6.md`
