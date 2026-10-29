---
id: FIX-UI-006
---

# FIX-UI-006 — Remover de files do UI-TASK-04 quatro paths não tocados pelo work commit

Origin: [UI-TASK-04](/docs/rite/cycles/interface-desktop/04-implementar-workspace-com-progresso-por-estagio.md)

## Problem

O item UI-TASK-04 lista `desktop/src-tauri/capabilities/default.json`,
`desktop/src-tauri/tauri.conf.json`, `desktop/package.json` e `desktop/package-lock.json` em
`files`, mas o work commit `72ebb52` não toca nenhum dos quatro — e nenhum outro commit da
UI-TASK-04 (`f02c3e9`, `bc8f249`) toca. Viola a regra promovida do CLAUDE.md (comparar `files`
com `git show --stat` nos dois sentidos antes de `rite finish`); mesma classe do defeito da
FIX-UI-005 (UI-TASK-03), tarefa e paths distintos.

## Evidência

```text
$ for f in desktop/src-tauri/capabilities/default.json desktop/src-tauri/tauri.conf.json desktop/package.json desktop/package-lock.json; do git show --name-only --format= 72ebb52 -- "$f"; done
(sem saída — nenhum dos quatro no commit)

$ git log --oneline --grep 'UI-TASK-04'
f02c3e9 test(e2e): add worker-path cold/warm probe for the UI pipeline
bc8f249 chore(rite): close UI-TASK-04
72ebb52 feat(desktop): run tablature from the workspace with live per-stage progress, cancel and errors

$ sh "$RITE_HOME/bin/rite" context UI-TASK-04 --json | grep -E 'capabilities/default\.json|tauri\.conf\.json|"desktop/package(-lock)?\.json"'
(imprime os quatro paths — estão em files)
```

## Root cause

Hipótese (não provada): os paths entraram em `files` no planejamento prevendo mudanças de
capabilities/dependências; a reconciliação pré-finish pegou a direção "tocado fora da lista"
(Files amended) mas não a direção "listado e não tocado".

## Fix

Via CLI do Rite (estado nunca editado à mão): `sh "$RITE_HOME/bin/rite" set UI-TASK-04
--files …` com a lista atual menos os quatro paths não tocados, mantendo os 13 paths reais,
o glob de evidências e os dois docs de tarefa amendados.

## Arquivos

- docs/rite/cycles/interface-desktop/04-implementar-workspace-com-progresso-por-estagio.md
- docs/rite/cycles/interface-desktop/progress.json

## Verificação

```text
$ sh "$RITE_HOME/bin/rite" context UI-TASK-04 --json | grep -E 'capabilities/default\.json|tauri\.conf\.json|desktop/package(-lock)?\.json'
```

Hoje imprime os quatro paths; depois do fix deve sair vazio.

## Execution Log

- 2026-10-29 — Triagem inline (`rite reproduce --all --cycle interface-desktop`): REPRODUCED.
  `git show --name-only 72ebb52` não lista nenhum dos quatro paths; context da UI-TASK-04
  imprime os quatro em `files`. Saída igual à Evidência.
- 2026-10-29 — Fix aplicado inline (trabalho é bookkeeping via CLI, vedado a workers):
  `rite set UI-TASK-04 --files …` com a lista anterior menos os quatro paths não tocados
  (13 entradas restantes, glob de evidências e docs amendados mantidos). Verificação: grep dos
  quatro no context sai vazio (exit 1); `rite check --quick` → errors: 0, warnings: 0.
- **Closed** — commit `da91083` (2026-10-29): chore(cycle): drop four untouched paths from UI-TASK-04 files
  - Files (`git show --name-status da91083`):
    - `M docs/rite/cycles/interface-desktop/FIX-UI-006.md`
    - `M docs/rite/cycles/interface-desktop/progress.json`
