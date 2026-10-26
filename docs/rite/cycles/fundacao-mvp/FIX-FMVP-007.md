---
id: FIX-FMVP-007
---

# FIX-FMVP-007 — Registrar pyproject.toml nos files declarados da FMVP-TASK-08

Origin: [FMVP-TASK-08](/docs/rite/cycles/fundacao-mvp/08-fechar-fase-1.md)

## Problem

O commit `1d4bdd3` modifica `pyproject.toml` (adiciona `"mido"` aos dev extras), mas a lista de
files declarados da task tem só `README.md`. O Execution Log já sinaliza "Outside declared files
(README.md): pyproject.toml" e as Notes justificam (encaminhado da FMVP-TASK-07) — a divergência
está documentada, mas o escopo declarado nunca foi emendado, deixando um descasamento permanente
entre o campo `files` do item e o diff entregue.

## Evidência

```text
$ git show --stat 1d4bdd3
 README.md      | 60 +++...
 pyproject.toml |  3 +++
```

(Campo `files` do item: `[README.md]` — ver `sh "$RITE_HOME/bin/rite" context FMVP-TASK-08 --json`.)

## Root cause

Hipótese: a dependência `mido` foi encaminhada da FMVP-TASK-07 durante a execução e commitada
junto com a mudança do README, sem antes emendar o campo `files` da task via CLI do Rite.

## Fix

Estado da task é gerido pelo Rite e muda só pela CLI:
`sh "$RITE_HOME/bin/rite" set FMVP-TASK-08 --files README.md,pyproject.toml` — ou o usuário
aceita a divergência registrada como final e este fix é dado como stale. Nunca editar
`progress.json` à mão.

## Arquivos

- `docs/rite/cycles/fundacao-mvp/progress.json` (via CLI)
- `docs/rite/cycles/fundacao-mvp/08-fechar-fase-1.md` (já documenta a divergência)

## Verificação

```text
$ sh "$RITE_HOME/bin/rite" context FMVP-TASK-08 --json | grep -q '"pyproject.toml"'
```

Falha hoje contra o campo `files`; deve passar quando os files declarados incluírem
`pyproject.toml` — ou o fix é descartado se a divergência registrada for aceita.

Medido após o fix (2026-10-26):

```text
$ sh "$RITE_HOME/bin/rite" context FMVP-TASK-08 --json | grep -c '"pyproject.toml"'   # antes
0
$ sh "$RITE_HOME/bin/rite" set FMVP-TASK-08 --files README.md,pyproject.toml
$ sh "$RITE_HOME/bin/rite" context FMVP-TASK-08 --json | grep -q '"pyproject.toml"'; echo "exit=$?"
exit=0
```

## Notas

Escopo declarado da FMVP-TASK-08 emendado via CLI (`rite set FMVP-TASK-08 --files
README.md,pyproject.toml`), fechando o descasamento com o diff entregue em `1d4bdd3`. O arquivo
da task já documentava a divergência; nenhuma edição manual de `progress.json`.

## Execution Log

- 2026-10-26 — Triagem (`rite reproduce FIX-FMVP-007`): REPRODUCED.

  ```text
  $ git show --stat 1d4bdd3
   README.md      | 60 ++++++++...
   pyproject.toml |  3 +++
  ```

  Campo `files` da FMVP-TASK-08 segue só com `README.md`.
