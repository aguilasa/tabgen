---
id: FIX-STEM-004
---

# FIX-STEM-004 — Justificar a reescrita do Escopo feita no commit de trabalho

Origin: [STEM-TASK-02](/docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md)

## Problem

O commit de trabalho `89dd225` reescreveu o Escopo da STEM-TASK-02: "20 s de um stem real
(`stems/guitar.wav`)" virou "Karplus-Strong sintetizado, 10 s". O Execution Log não tem entrada de
alteração com o motivo.

## Evidência

```text
$ git show 89dd225 -- docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md | grep -E '^[-+] +- (Pega|Sintetiza)'
-    - Pega 20 s de um stem real (o padrão é o `stems/guitar.wav` da raiz, se existir; senão, um sinal
+    - Sintetiza um stem de guitarra determinístico (Karplus-Strong, 10 s) e roda
$ sed -n '/## Execution Log/,$p' docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md | grep -i amended
(vazio)
```

## Root cause

A especificação foi ajustada ao que foi construído (motivo válido: `stems/guitar.wav` não é versionado), mas a mudança não foi registrada.

## Fix

Acrescentar ao Execution Log uma entrada "Scope amended" com o motivo (reprodutibilidade a partir do HEAD, regra do CLAUDE.md).

## Arquivos

- docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md

## Verificação

`sed -n '/## Execution Log/,$p' docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md | grep -i amended` acha a linha.

## Execution Log

- **Closed** — commit `153bb1f` (2026-11-21): docs(rite): record the STEM-TASK-02 scope amendment
  - Files (`git show --name-status 153bb1f`):
    - `M docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md`
