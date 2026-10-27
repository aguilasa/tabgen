---
id: FIX-ANA-002
---

# FIX-ANA-002 — Remover tests/test_pipeline.py obsoleto dos files da ANA-TASK-05

Origin: [ANA-TASK-05](/docs/rite/cycles/archive/analise-musical/05-orquestrar-analise-no-pipeline-com-cache-e.md)

## Problem

A lista `files` da ANA-TASK-05 no estado do ciclo declara `tests/test_pipeline.py`, mas o
commit de trabalho (`1455cf0`) nunca toca esse arquivo — os testes novos foram para
`tests/test_analysis_pipeline.py`. O metadado aponta para onde o trabalho da task não está.

## Evidência

```text
$ grep -n "test_pipeline" docs/rite/cycles/analise-musical/progress.json | head -1
105:      "files": ["tabgen/core/pipeline.py", "tabgen/cli/main.py", "tests/test_pipeline.py", "tests/test_analysis_pipeline.py"],
$ git show --stat 1455cf0
(toca 05-....md, tabgen/cli/main.py, tabgen/core/pipeline.py, tests/test_analysis_pipeline.py — sem tests/test_pipeline.py)
```

## Root cause

Hipótese (não provada): o plano previa estender o `tests/test_pipeline.py` existente; a
execução criou arquivo dedicado (`tests/test_analysis_pipeline.py`) e o campo `files` do
planejamento nunca foi corrigido.

## Fix

Estado do ciclo muda só pela CLI do Rite — nunca editar `progress.json` à mão. Corrigir o
campo pela CLI:

```text
$ sh "$RITE_HOME/bin/rite" set ANA-TASK-05 --files tabgen/core/pipeline.py,tabgen/cli/main.py,tests/test_analysis_pipeline.py
```

Alternativa: o usuário aceitar o drift e marcar este fix como stale.

## Arquivos

- `docs/rite/cycles/analise-musical/progress.json` (via CLI do Rite, nunca à mão)

## Verificação

```text
$ grep -A1 '"id": "ANA-TASK-05"' docs/rite/cycles/analise-musical/progress.json >/dev/null && grep -c "tests/test_pipeline.py" docs/rite/cycles/analise-musical/progress.json
```

Hoje retorna ≥1 (a entrada da ANA-TASK-05, linha 105); depois do fix deve retornar 0 e
`sh "$RITE_HOME/bin/rite" check --quick --json` seguir com 0 erros.

Medido após o fix (2026-10-27):

```text
$ sh "$RITE_HOME/bin/rite" set ANA-TASK-05 --files tabgen/core/pipeline.py,tabgen/cli/main.py,tests/test_analysis_pipeline.py
$ grep -c "tests/test_pipeline.py" docs/rite/cycles/analise-musical/progress.json
0
$ sh "$RITE_HOME/bin/rite" check --quick --json
"errors": 0
```

## Notas

Campo `files` da ANA-TASK-05 emendado via CLI, removendo `tests/test_pipeline.py` (nunca tocado
pelo work commit `1455cf0`) e mantendo os três arquivos entregues. Nenhuma edição manual de
`progress.json`.

## Execution Log

- 2026-10-27 — Triagem (`rite reproduce FIX-ANA-002`): REPRODUCED.

  ```text
  $ grep -n "test_pipeline" docs/rite/cycles/analise-musical/progress.json | head -1
  105:      "files": ["tabgen/core/pipeline.py", "tabgen/cli/main.py", "tests/test_pipeline.py", "tests/test_analysis_pipeline.py"],
  $ git show --stat 1455cf0
  (toca 05-....md, tabgen/cli/main.py, tabgen/core/pipeline.py, tests/test_analysis_pipeline.py — sem tests/test_pipeline.py)
  ```
- **Closed** — commit `b6cc2ed` (2026-10-27): chore(cycle): drop untouched tests/test_pipeline.py from ANA-TASK-05 files
  - Files (`git show --name-status b6cc2ed`):
    - `M docs/rite/cycles/analise-musical/progress.json`
