---
id: FIX-STEM-003
---

# FIX-STEM-003 — Registrar o tempo medido do probe no Execution Log

Origin: [STEM-TASK-02](/docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md)

## Problem

O critério 2 da STEM-TASK-02 está marcado e diz que o tempo medido vai para o Execution Log, mas o
arquivo da tarefa não registra tempo nenhum. O bloco de evidência foi escrito numa seção
`## Notes` que não existia no corpo, e a substituição não fez nada.

## Evidência

```text
$ sed -n '/## Execution Log/,$p' docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md | grep -E "cold export: [0-9.]+ s"
(vazio)
```

## Root cause

O corpo da tarefa foi escrito sem a seção `## Notes`, e a evidência foi inserida por uma substituição que não achou o alvo.

## Fix

Acrescentar sob o Execution Log a saída do probe (`.venv/bin/python scripts/probe_e2e_stems.py`) com os tempos a frio e com cache e o comando.

## Arquivos

- docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md

## Verificação

`sed -n '/## Execution Log/,$p' docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md | grep -E "cold export: [0-9.]+ s"` acha a linha.

## Execution Log

- **Closed** — commit `e0be64f` (2026-11-21): docs(rite): record STEM-TASK-02 probe timings
  - Files (`git show --name-status e0be64f`):
    - `M docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md`
