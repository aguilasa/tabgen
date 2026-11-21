---
id: FIX-STEM-007
---

# FIX-STEM-007 — Registrar a evidência das checagens 2 e 3 da Fase 6

Origin: [STEM-TASK-03](/docs/rite/cycles/entrada-stems/03-fechar-fase-6.md)

## Problem

O Escopo da STEM-TASK-03 pede rodar e registrar as checagens da Fase 6 do profile. As Notes registram
só as checagens 1 (probe) e 4 (gates e grep). As checagens 2 (`--stem` com a mistura como entrada) e 3
(versões de cache sem `--stem` iguais às do HEAD anterior ao ciclo) não têm comando nem saída.

## Evidência

```text
$ grep -nE "test_versions_without_user_stems_are_unchanged|adds_the_mix" docs/rite/cycles/entrada-stems/03-fechar-fase-6.md
(vazio)
```

## Root cause

O fechamento seguiu a lista de Done criteria, que não inclui as checagens 2 e 3, e não a lista do profile.

## Fix

Acrescentar às Notes da tarefa os comandos e as saídas das checagens 2 e 3 (seleção do pytest).

## Arquivos

- docs/rite/cycles/entrada-stems/03-fechar-fase-6.md

## Verificação

`grep -nE "test_versions_without_user_stems_are_unchanged|adds_the_mix" docs/rite/cycles/entrada-stems/03-fechar-fase-6.md` lista as duas.

## Execution Log

- **Closed** — commit `0d6a334` (2026-11-21): docs(rite): record phase 6 checks 2 and 3 evidence
  - Files (`git show --name-status 0d6a334`):
    - `M docs/rite/cycles/entrada-stems/03-fechar-fase-6.md`
