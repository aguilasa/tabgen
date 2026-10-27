---
id: FIX-TAB-004
---

# FIX-TAB-004 — Declare golden ascii_guitar_riff.txt in TAB-TASK-06 files metadata

Origin: [TAB-TASK-06](/docs/rite/cycles/archive/tablatura/06-exportar-musicxml-via-music21-e-tab-ascii.md)

## Problem

O commit de trabalho da TAB-TASK-06 (`ee5892e`) altera dois arquivos ausentes da lista `files`
da tarefa: `tests/golden/ascii_guitar_riff.txt` (artefato do qual um done criterion depende) e
`docs/rite/cycles/tablatura/07-orquestrar-tablatura-no-pipeline-com-cache-e.md` (nota para
tarefa dependente). O Execution Log declara ambos honestamente, mas o metadado `files` ficou
incompleto em relação ao trabalho entregue.

## Evidência

```text
$ git show --name-status ee5892e | tail -8
M	docs/rite/cycles/tablatura/07-orquestrar-tablatura-no-pipeline-com-cache-e.md
A	tests/golden/ascii_guitar_riff.txt

$ sh "$RITE_HOME/bin/rite" context TAB-TASK-06 --json | grep -c ascii_guitar_riff.txt
(aparece só no texto do log, não em item.files)
```

## Root cause

Hipótese (não provada): a lista `files` foi escrita no planejamento, antes de o golden e a nota
cruzada existirem, e não foi emendada no fechamento.

## Fix

Emendar via CLI — nunca editar `progress.json` à mão:

```text
sh "$RITE_HOME/bin/rite" set TAB-TASK-06 --files pyproject.toml,tabgen/core/export/musicxml.py,tabgen/core/export/ascii_tab.py,tests/test_musicxml_export.py,tests/test_ascii_tab.py,tests/golden/ascii_guitar_riff.txt
```

Nota cruzada no doc da TASK-07 não entra em `files` (pertence à execução da própria TASK-07).

## Arquivos

- docs/rite/cycles/tablatura/progress.json (via CLI apenas)

## Verificação

```text
sh "$RITE_HOME/bin/rite" context TAB-TASK-06 --json | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); assert 'tests/golden/ascii_guitar_riff.txt' in d['item']['files']"
```

Falha agora (`AssertionError`); deve passar após o fix. Depois:
`sh "$RITE_HOME/bin/rite" check --quick --json` com 0 erros.

## Execution Log

- 2026-10-27 — Triagem inline (`rite reproduce --all --cycle tablatura`): REPRODUCED.
  `git show --name-status ee5892e` lista `A tests/golden/ascii_guitar_riff.txt` e
  `M docs/.../07-orquestrar...md`; `rite context TAB-TASK-06 | grep -c ascii_guitar_riff.txt` → 1
  (só no texto do log, não em `item.files`). Metadado segue incompleto no HEAD.
- 2026-10-27 — Fix aplicado inline (trabalho é bookkeeping via CLI, vedado a workers):
  `rite set TAB-TASK-06 --files pyproject.toml,tabgen/core/export/musicxml.py,tabgen/core/export/ascii_tab.py,tests/test_musicxml_export.py,tests/test_ascii_tab.py,tests/golden/ascii_guitar_riff.txt`.
  Antes: `item.files` com 5 entradas, sem o golden. Depois: assert da Verificação passa
  (`tests/golden/ascii_guitar_riff.txt` presente em `item.files`); `rite check --quick` →
  errors: 0, warnings: 0. Nota cruzada no doc da TASK-07 deixada fora de `files`, conforme o Fix.
- **Closed** — commit `e0429ee` (2026-10-27): chore(cycle): declare golden ascii_guitar_riff.txt in TAB-TASK-06 files
  - Files (`git show --name-status e0429ee`):
    - `M docs/rite/cycles/tablatura/FIX-TAB-004.md`
    - `M docs/rite/cycles/tablatura/progress.json`
