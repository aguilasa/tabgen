# Retro — analise-musical

Date: 2026-10-27

## Numbers

Fonte: `rite stats analise-musical --json`.

- Tarefas: 6 (6 done, 0 pending/blocked/skipped).
- Fixes: 2 (2 done, 0 stale); severidade: 0 critical, 0 high, 1 medium, 1 low.
- Fixes por tarefa: 0,33 (ciclo anterior fundacao-mvp: 0,88). Fase 2: 6 tarefas / 2 fixes.
- Origem: ANA-TASK-01 = 1; ANA-TASK-05 = 1.
- Latência de review: mediana 0 dias, máx 1 (6 revisadas).
- Tempo ativo: tarefas total 3652 s (mediana 406,5 s, máx 1618 s); fixes total 249 s (mediana 124,5 s).

## Root-cause groups

| Grupo | Qtd | Tipo | Fixes |
|---|---|---|---|
| Composição real sem teste: único teste do caminho stubava a função que monta a lista (`run_checks`) | 1 | engineering | FIX-ANA-001 |
| `files` declarados do item divergem do work commit (aqui: declarado e não tocado) | 1 | bookkeeping | FIX-ANA-002 |

Totais: engineering 1, bookkeeping 1.

## Proposals

### Keep in next profile

Para `docs/rite/profiles/analise-musical.pitfalls.md`:

```markdown
### Teste da composição real, não só do stub
- tags: tests, mocks, doctor, pipeline
- paths: tests/**
- proven by: FIX-ANA-001 (2026-10-26)
- rule: ao adicionar um item a uma função que compõe uma lista (checks, estágios), ter um teste que chama a função real sem monkeypatch e assere o item; provar com defeito plantado.
```

E ampliar a entrada existente "Emendar files declarados antes de commitar fora do escopo":
`proven by: FIX-FMVP-007 (2026-10-26), FIX-ANA-002 (2026-10-27)`; `rule: antes do rite finish,
comparar os files do item com git show --stat do work commit nos dois sentidos (arquivo tocado
fora da lista, arquivo listado e não tocado) e corrigir com rite set <ID> --files ...`.

### Promote to rite.toml / CLAUDE.md

- **Files declarados = diff entregue** (FIX-FMVP-007 + FIX-ANA-002, dois ciclos). Linha no
  `CLAUDE.md`: "Antes de `rite finish`, conferir `files` do item contra `git show --stat` do work
  commit nos dois sentidos; corrigir com `rite set <ID> --files …`."
- Gates: o profile deste ciclo ficou sem `## Gates`, mas nenhum fix resultou (critérios das
  tarefas já citavam `.venv/bin/`). Sem segunda evidência; segue não promovido.

### Rite issues (plugin)

Comentário para https://github.com/aguilasa/rite/issues/23 (mesma família):

> Second occurrence, opposite direction (cycle analise-musical): ANA-TASK-05 declared
> `tests/test_pipeline.py`, the work commit `1455cf0` never touched it, and `finish` reported
> nothing. The review then opened FIX-ANA-002 just to run `rite set ANA-TASK-05 --files …`.
> Suggest `finish` also reports declared files the work commit did not touch, with the same
> amend option proposed above.

### Prune

Nenhuma. Profile com hint comments e checks da Fase 2 ainda válidos; pitfalls herdados não
foram contrariados por fix.

## Applied

- Keep: pitfall "Teste da composição real, não só do stub" adicionado e entrada de files declarados ampliada em `docs/rite/profiles/analise-musical.pitfalls.md` (FIX-ANA-001, FIX-ANA-002).
- Report: comentário em https://github.com/aguilasa/rite/issues/23#issuecomment-6445445220 (FIX-ANA-002).
- Não aplicado (decisão do usuário): Promote da regra files declarados = diff no `CLAUDE.md`.
