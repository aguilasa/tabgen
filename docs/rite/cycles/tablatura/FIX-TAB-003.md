---
id: FIX-TAB-003
---

# FIX-TAB-003 — Correct quoted version-command output in TAB-TASK-05 verification

Origin: [TAB-TASK-05](/docs/rite/cycles/tablatura/05-exportar-gp5-via-pyguitarpro.md)

## Problem

A seção Verificação do doc da TAB-TASK-05 cita a saída do comando de versão como
`pyguitarpro 0.11`, mas o comando imprime apenas `0.11`. O número em si reproduz; só a linha de
saída citada está errada (o parágrafo anterior de Notes registra a saída correta).

## Evidência

```text
$ .venv/bin/python -c "import importlib.metadata; print(importlib.metadata.version('pyguitarpro'))"
0.11

$ grep -n "pyguitarpro 0.11" docs/rite/cycles/tablatura/05-exportar-gp5-via-pyguitarpro.md
61:  → `pyguitarpro 0.11`; pin em `pyproject.toml`: `"pyguitarpro==0.11"`
```

## Root cause

Hipótese (não provada): a nota de verificação foi digitada à mão combinando nome do pacote e
versão em vez de colar a saída do comando.

## Fix

Editar a linha 61 de `docs/rite/cycles/tablatura/05-exportar-gp5-via-pyguitarpro.md` para citar
a saída real `0.11`. A edição é em prosa da seção Verificação — nunca tocar frontmatter nem
blocos `<!-- rite:begin … -->`/`<!-- rite:end -->`; estado só via CLI
(`sh "$RITE_HOME/bin/rite"`).

## Arquivos

- docs/rite/cycles/tablatura/05-exportar-gp5-via-pyguitarpro.md

## Verificação

```text
grep -n '`pyguitarpro 0.11`' docs/rite/cycles/tablatura/05-exportar-gp5-via-pyguitarpro.md
```

Sai 0 agora (linha 61 encontrada); deve sair 1 (nada encontrado) após o fix. Depois:
`sh "$RITE_HOME/bin/rite" check --quick --json` com 0 erros.

## Execution Log
