---
id: FIX-UI-005
---

# FIX-UI-005 — Remover de files do UI-TASK-03 dois paths não tocados pelo work commit

Origin: [UI-TASK-03](/docs/rite/cycles/interface-desktop/03-implementar-tela-inicio-com-abertura-de-arquivo.md)

## Problem

O item UI-TASK-03 lista `desktop/src/lib/worker.ts` e `desktop/src-tauri/tauri.conf.json` em
`files`, mas o work commit `d96d198` não toca nenhum dos dois (worker.ts foi tocado por
`b8bd761`/`72ebb52`; tauri.conf.json só por `b8bd761`). A regra promovida do CLAUDE.md
(FIX-FMVP-007, FIX-ANA-002, FIX-TAB-004, FIX-TAB-006) exige reconciliar `files` com
`git show --stat` nos dois sentidos antes de `rite finish`; a direção "listado e não tocado"
não foi corrigida — o Files amended só adicionou o doc da UI-TASK-04.

## Evidência

```text
$ git show --name-status d96d198 | grep -E "worker\.ts|tauri\.conf\.json"
(sem saída — nenhum dos dois no commit)

$ git log --oneline --all -- desktop/src-tauri/tauri.conf.json
b8bd761 feat(desktop): scaffold Tauri app with worker sidecar and Ambiente screen

$ sh "$RITE_HOME/bin/rite" context UI-TASK-03 --json | grep -E "worker\.ts|tauri\.conf\.json"
      "desktop/src/lib/worker.ts",
      "desktop/src-tauri/tauri.conf.json",
```

## Root cause

Hipótese (não provada): a lista de files foi escrita no planejamento prevendo mexer no
worker.ts e no tauri.conf.json; o batch com UI-TASK-04 concentrou essas mudanças na outra
tarefa, e a reconciliação pré-finish só olhou a direção "tocado fora da lista".

## Fix

Via CLI do Rite (estado nunca editado à mão): `sh "$RITE_HOME/bin/rite" set UI-TASK-03
--files …` com a lista atual menos os dois paths; progress.json/md regenerados pela CLI.

## Arquivos

- docs/rite/cycles/interface-desktop/03-implementar-tela-inicio-com-abertura-de-arquivo.md
- docs/rite/cycles/interface-desktop/progress.json

## Verificação

```text
$ sh "$RITE_HOME/bin/rite" context UI-TASK-03 --json | grep -E "desktop/src/lib/worker\.ts|desktop/src-tauri/tauri\.conf\.json"
```

Deve sair vazio (hoje imprime as duas linhas).

## Execution Log
