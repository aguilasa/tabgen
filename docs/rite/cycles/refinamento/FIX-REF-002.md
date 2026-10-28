---
id: FIX-REF-002
---

# FIX-REF-002 — Remove .gitignore from REF-TASK-06 files metadata

Origin: [REF-TASK-06](/docs/rite/cycles/refinamento/06-criar-harness-de-avaliacao-em-guitarset-e-egdb.md)

## Problem

O REF-TASK-06 declara `.gitignore` em `files`, mas nenhum commit da task tocou esse arquivo
(`.gitignore` mudou pela última vez em `64f438b`, TAB-TASK-08). Viola a regra promovida do
CLAUDE.md: comparar `files` com `git show --stat` nos dois sentidos antes do finish (arquivo
listado e não tocado → `rite set --files`).

## Evidência

```text
$ git show --name-only d0d38b4 | grep -x ".gitignore"
(vazio, exit 1)

$ git log --oneline -1 -- .gitignore
64f438b docs(readme): document tabgen export with measured runtimes and limitations
```

## Root cause

Hipótese: `.gitignore` entrou na lista prevista no planejamento (para ignorar dados de dataset),
mas ficou desnecessário porque os datasets moram fora do repositório (`~/datasets/tabgen/`), e a
lista não foi ajustada no finish.

## Fix

Emendar via CLI — nunca editar `progress.json` à mão:

```text
sh "$RITE_HOME/bin/rite" set REF-TASK-06 --files scripts/eval/__init__.py,scripts/eval/run.py,scripts/eval/metrics.py,scripts/eval/subsets/guitarset.txt,scripts/eval/subsets/egdb.txt,tests/test_eval_metrics.py,scripts/eval/download.py,scripts/eval/loaders.py,scripts/eval/reports/egdb-egdb.json,scripts/eval/reports/egdb-egdb.md,scripts/eval/reports/guitarset-guitarset.json,scripts/eval/reports/guitarset-guitarset.md
```

(Lista atual sem `.gitignore`.)

## Arquivos

- docs/rite/cycles/refinamento/progress.json (via CLI apenas)

## Verificação

```text
sh "$RITE_HOME/bin/rite" context REF-TASK-06 --json | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); sys.exit(1 if '.gitignore' in d['item']['files'] else 0)"
```

Sai 1 agora; deve sair 0 após o fix. Depois:
`sh "$RITE_HOME/bin/rite" check --quick --json` com 0 erros.

## Execution Log

- 2026-10-28 — Triagem inline (`rite reproduce --all --cycle refinamento`): REPRODUCED.
  `git show --name-only d0d38b4 | grep -x ".gitignore"` → vazio, exit 1 (commit da task não toca
  o arquivo); `git log --oneline -1 -- .gitignore` → `64f438b` (TAB-TASK-08). `.gitignore` segue
  declarado em `files` da REF-TASK-06 sem ter sido tocado.
- 2026-10-28 — Fix aplicado inline (trabalho é bookkeeping via CLI, vedado a workers):
  `rite set REF-TASK-06 --files …` com a lista atual sem `.gitignore` (12 entradas de
  scripts/eval + tests). Verificação: script da seção sai 0 (`.gitignore` ausente de
  `item.files`); `rite check --quick` → errors: 0, warnings: 0.
