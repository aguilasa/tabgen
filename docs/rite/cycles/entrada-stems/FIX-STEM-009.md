---
id: FIX-STEM-009
---

# FIX-STEM-009 — Contar as notas de 29/10 e do export novo pelo mesmo método

Origin: [STEM-TASK-03](/docs/rite/cycles/entrada-stems/03-fechar-fase-6.md)

## Problem

As Notes comparam "516 notes" (resumo do tabgen, que não conta ligaduras) com "o .gp5 de 509 notas"
de 29/10, sem comando para o 509. Contadas pelo PyGuitarPro, 509 inclui as ligaduras. Pelo mesmo
método, o antigo tem 506 notas sem ligadura contra 516 agora, ou 509 contra 525 contando todas.

## Evidência

```text
$ grep -n "509 notas" docs/rite/cycles/entrada-stems/03-fechar-fase-6.md
(linha sem comando ao lado)
```

## Root cause

O 509 veio da soma de `beat.notes`, e o 516, do resumo do tabgen: dois métodos diferentes.

## Fix

Contar os dois arquivos com o mesmo script PyGuitarPro e registrar o comando com as duas contagens.

## Arquivos

- docs/rite/cycles/entrada-stems/03-fechar-fase-6.md

## Verificação

`grep -n "nontie" docs/rite/cycles/entrada-stems/03-fechar-fase-6.md` mostra as contagens dos dois arquivos pelo mesmo método.

## Execution Log

- **Closed** — commit `99add44` (2026-11-21): docs(rite): compare note counts with one method in STEM-TASK-03
  - Files (`git show --name-status 99add44`):
    - `M docs/rite/cycles/entrada-stems/03-fechar-fase-6.md`
