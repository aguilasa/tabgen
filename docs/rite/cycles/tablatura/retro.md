# Retro — tablatura

Date: 2026-10-27

## Numbers

Fonte: `rite stats tablatura --json`.

- Tarefas: 8 (8 done, 0 pending/blocked/skipped).
- Fixes: 6 (6 done, 0 stale); severidade: 0 critical, 1 high, 2 medium, 3 low.
- Fixes por tarefa: 0,75 (fundacao-mvp 0,88; analise-musical 0,33). Fase 3: 8 tarefas / 6 fixes.
- Origem: TAB-TASK-01, 04, 05, 06, 07, 08 = 1 cada.
- Latência de review: mediana 0 dias, máx 0 (8 revisadas).
- Tempo ativo: tarefas total 4686 s (mediana 680 s); fixes total 1501 s (mediana 282,5 s); review total 3553 s (mediana 368 s).

## Root-cause groups

| Grupo | Qtd | Tipo | Fixes |
|---|---|---|---|
| `files` declarados não emendados quando o work commit tocou arquivo extra | 2 | bookkeeping | FIX-TAB-004, FIX-TAB-006 |
| Números de verificação sem probe versionado (medidos em arquivo de scratchpad) | 1 | engineering | FIX-TAB-005 |
| Convenção de contrato decidida numa tarefa e contrariada em outra; encaminhamento só em prosa de tarefa fechada | 1 | engineering | FIX-TAB-001 |
| Comparação por string renderizada em vez de valor parseado, com grafia divergente da lib externa (madmom) | 1 | engineering | FIX-TAB-002 |
| Saída de comando citada digitada à mão, não colada | 1 | bookkeeping | FIX-TAB-003 |

Totais: engineering 3, bookkeeping 3.

Recorrências: o grupo de `files` aparece no 3º ciclo seguido (FIX-FMVP-007, FIX-ANA-002) e o de
probe no 2º (FIX-FMVP-005, FIX-FMVP-006), **ambos com pitfall herdado no arquivo** — o pitfall
não bastou para evitar.

## Proposals

### Keep in next profile

Novas entradas para `docs/rite/profiles/tablatura.pitfalls.md`:

```markdown
### Convenção de contrato fica no contrato, não em prosa de tarefa
- tags: contract, models, conventions
- paths: tabgen/core/models.py, tabgen/core/**
- proven by: FIX-TAB-001 (2026-10-27)
- rule: quando uma tarefa produz valores de um campo cuja semântica outra tarefa definiu (ex.: numeração de corda), conferir e alinhar o docstring do contrato no mesmo commit; encaminhamento em Notes de tarefa fechada não conta.

### Comparar valores parseados, não strings renderizadas
- tags: analysis, key, labels, external-lib
- paths: tabgen/core/analysis/**
- proven by: FIX-TAB-002 (2026-10-27)
- rule: igualdade de rótulos musicais (tom, acorde) compara `(pitch_class, mode)`/campos parseados; grafia canônica casa com a da lib que produz o rótulo, testada por modo.

### Saída citada é colada, não digitada
- tags: verification, notes
- paths: docs/rite/cycles/**
- proven by: FIX-TAB-003 (2026-10-27)
- rule: linha de saída citada em Verificação/Notes é cópia literal do terminal.
```

Atualizar entradas existentes:
- "Emendar files declarados…": `proven by` += `FIX-TAB-004, FIX-TAB-006 (2026-10-27)`.
- "Números em Notes/README exigem probe versionado": `proven by` += `FIX-TAB-005 (2026-10-27)`;
  `rule` += "cada comando de e2e (`separate`, `transcribe`, `analyze`, `export`) tem probe em
  `scripts/probe_e2e_*.py` sobre amostra gerada; arquivo de scratchpad não é evidência".

### Promote to rite.toml / CLAUDE.md

1. **Files declarados = diff** — 4 fixes em 3 ciclos (FIX-FMVP-007, FIX-ANA-002, FIX-TAB-004,
   FIX-TAB-006). Recusado nas duas retros anteriores; a recorrência mostra que o pitfall sozinho
   não segura. Linha no `CLAUDE.md`:
   "Antes de `rite finish`, comparar os `files` do item com `git show --stat` do work commit nos
   dois sentidos e corrigir com `rite set <ID> --files …`."
2. **Probe versionado para números de e2e** — 3 fixes em 2 ciclos (FIX-FMVP-005, FIX-FMVP-006,
   FIX-TAB-005). Linha no `CLAUDE.md`:
   "Número de verificação e2e só vale com comando reproduzível do HEAD: probe em
   `scripts/probe_e2e_*.py` sobre amostra gerada; arquivos de scratchpad não são evidência."

### Rite issues (plugin)

Comentário para https://github.com/aguilasa/rite/issues/23:

> Third cycle in a row (tablatura): FIX-TAB-004 and FIX-TAB-006 again only ran `rite set <ID>
> --files …` after `finish` had already logged "Outside declared files". The repository's
> inherited pitfall for exactly this did not prevent it: pitfalls are searched by commands, but
> `finish` does not consult them. An amend option at `finish` would have avoided 4 fixes across
> 3 cycles.

### Prune

Nenhuma. Profile em 3260 bytes; pitfalls herdados ainda aplicáveis.

## Applied

- Keep: 3 pitfalls novos (FIX-TAB-001, FIX-TAB-002, FIX-TAB-003) e 2 entradas atualizadas (files: FIX-TAB-004, FIX-TAB-006; probe: FIX-TAB-005) em `docs/rite/profiles/tablatura.pitfalls.md`.
- Report: comentário em https://github.com/aguilasa/rite/issues/23#issuecomment-6452493078 (FIX-TAB-004, FIX-TAB-006).
- Não aplicados (decisão do usuário): Promote files = diff e Promote probe e2e no `CLAUDE.md`.
