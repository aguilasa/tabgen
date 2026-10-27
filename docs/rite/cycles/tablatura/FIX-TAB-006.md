---
id: FIX-TAB-006
---

# FIX-TAB-006 — Declare .gitignore in TAB-TASK-08 files metadata

Origin: [TAB-TASK-08](/docs/rite/cycles/tablatura/08-fechar-fase-3.md)

## Problem

O commit de trabalho da TAB-TASK-08 (`64f438b`) modifica `.gitignore` (adiciona `out/`), mas a
lista `files` da tarefa declara só `README.md`. O Execution Log revela a deriva ("Outside
declared files"), porém a declaração nunca foi emendada — ao contrário do precedente do próprio
ciclo (`e0429ee` emendou os `files` da TAB-TASK-06 pela mesma deriva).

## Evidência

```text
$ git show --name-status 64f438b
M	.gitignore
M	README.md
M	docs/rite/cycles/tablatura/08-fechar-fase-3.md

$ sh "$RITE_HOME/bin/rite" context TAB-TASK-08 --json | grep -c '"\.gitignore"'
0
```

## Root cause

Hipótese (não provada): o ignore de `out/` foi adicionado oportunisticamente ao copiar saídas do
e2e e a declaração de `files` não foi atualizada antes do fechamento.

## Fix

Emendar via CLI — nunca editar `progress.json` à mão:

```text
sh "$RITE_HOME/bin/rite" set TAB-TASK-08 --files README.md,.gitignore
```

## Arquivos

- docs/rite/cycles/tablatura/progress.json (via CLI apenas)

## Verificação

```text
sh "$RITE_HOME/bin/rite" context TAB-TASK-08 --json | grep '"\.gitignore"'
```

Sai 1 agora (nada encontrado); deve sair 0 após o fix. Depois:
`sh "$RITE_HOME/bin/rite" check --quick --json` com 0 erros.

## Execution Log

- 2026-10-27 — Triagem inline (`rite reproduce --all --cycle tablatura`): REPRODUCED.
  `git show --name-status 64f438b` lista `M .gitignore` além de README.md e doc 08;
  `rite context TAB-TASK-08 | grep -c '".gitignore"'` → 0 (ausente de `item.files`).
- 2026-10-27 — Fix aplicado inline (trabalho é bookkeeping via CLI, vedado a workers):
  `rite set TAB-TASK-08 --files README.md,.gitignore`. Verificação: grep de `".gitignore"` no
  context da TAB-TASK-08 agora sai 0 (encontrado); `rite check --quick` → errors: 0, warnings: 0.
- **Closed** — commit `1900607` (2026-10-27): chore(cycle): declare .gitignore in TAB-TASK-08 files
  - Files (`git show --name-status 1900607`):
    - `M docs/rite/cycles/tablatura/FIX-TAB-006.md`
    - `M docs/rite/cycles/tablatura/progress.json`
