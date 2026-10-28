# Retro — refinamento

Date: 2026-10-28

## Numbers

Fonte: `rite stats refinamento --json`.

- Tarefas: 9 (9 done, 0 pending/blocked/skipped). REF-TASK-09 entrou durante o ciclo (integração
  do Riley atrás de `--transcriber`, após a decisão da REF-TASK-07).
- Fixes: 3 (2 done, 1 stale); severidade: 0 critical, 0 high, 2 medium, 1 low.
- Fixes por tarefa: 0,33 (fundacao-mvp 0,88; analise-musical 0,33; tablatura 0,75). Fase 4: 9 tarefas / 3 fixes.
- Origem: REF-TASK-06 = 2; REF-TASK-04 = 1.
- Latência de review: mediana 0 dias, máx 0 (9 revisadas).
- Tempo ativo: tarefas total 114276 s (mediana 554 s, máx 54888 s — uma tarefa ficou aberta ~15 h,
  provavelmente esperando download/avaliação); fixes total 369 s; review total 3070 s (mediana 339 s).

## Root-cause groups

| Grupo | Qtd | Tipo | Fixes |
|---|---|---|---|
| Pendência da tarefa encaminhada só em prosa (edição negada pela permissão) e tarefa fechada assim mesmo | 1 | engineering | FIX-REF-001 |
| `files` declarados com arquivo nunca tocado (regra já no `CLAUDE.md`) | 1 | bookkeeping | FIX-REF-002 |
| Check de fase citando recurso de tarefa ainda pendente, medido por revisores de outras tarefas da fase (stale depois da REF-TASK-05) | 1 | bookkeeping | FIX-REF-003 |

Totais: engineering 1, bookkeeping 2.

## Proposals

`rite retro-suggest refinamento --json` deu 2 Keep, 5 Promote, 0 Prune, 0 carry-over. Parte dos
casamentos é falso positivo (ver Report): FIX-REF-001 casou "Cache hit valida identidade" e
FIX-REF-002 casou "probe versionado" e "saída colada" só porque os globs `tabgen/core/**` e
`docs/rite/cycles/**` são largos. Aceitos abaixo só os casamentos de causa raiz.

### Keep in next profile

- (retro-suggest) FIX-REF-002 → atualizar "Emendar files declarados…": `proven by` +=
  `FIX-REF-002 (2026-10-28)`; acrescentar à `rule`: "a regra do `CLAUDE.md` sozinha não bastou;
  rodar a comparação como último passo antes do `rite finish`, não de memória".
- (retro-suggest, causa raiz conferida) FIX-REF-001 → atualizar "Convenção de contrato fica no
  contrato, não em prosa de tarefa": `proven by` += `FIX-REF-001 (2026-10-28)`; acrescentar à
  `rule`: "o mesmo vale para qualquer pendência da tarefa (edição negada pela permissão,
  comentário a corrigir): ou é feita, ou vira fix pela CLI (`rite new-fix`), ou a tarefa fica
  blocked — nunca só em Notes/Execution Log".
- (added) FIX-REF-003 → nova entrada:

```markdown
### Check de fase só cita recurso já entregue ou marcado com a tarefa dona
- tags: profile, phase-checks, review
- paths: docs/rite/profiles/*.md
- proven by: FIX-REF-003 (2026-10-28)
- rule: ao escrever checks de fase no planejamento, anotar a tarefa que entrega cada recurso citado (ex.: "(REF-TASK-05)"); revisor que encontra o check vermelho com a tarefa dona pendente registra nota, não fix.
```

### Promote to rite.toml / CLAUDE.md

- (retro-suggest, causa raiz conferida) "Pendência só em prosa" — FIX-TAB-001 + FIX-REF-001, dois
  ciclos. Linha no `CLAUDE.md`: "Pendência que a tarefa não conclui (edição negada, decisão
  encaminhada) vira fix pela CLI (`rite new-fix`) ou deixa a tarefa blocked; nunca fica só em
  prosa de tarefa fechada."
- "Files declarados = diff" já está no `CLAUDE.md` (promovido em 2026-10-27) e recorreu
  (FIX-REF-002): nada mais a promover no repositório; o próximo nível é o próprio Rite (Report).
- Rejeitados (falso positivo do casamento por path): "Cache hit valida identidade" (FIX-REF-001
  não é cache), "Números … probe versionado" e "Saída citada é colada" (FIX-REF-002 não é número
  nem saída citada).

### Rite issues (plugin)

1. Comentário para https://github.com/aguilasa/rite/issues/24 (retro-suggest, já entregue na 0.26.0):

> Tried `retro-suggest` on cycle refinamento (rite 0.26.0). Two problems:
> 1. `"previous": "analise-musical"`, but the most recent cycle before `refinamento` is
>    `tablatura` (created 2026-10-27 13:00, archived 17:17; `refinamento`'s pitfalls were copied
>    from it via `--pitfalls-from tablatura`). `carry_over` is therefore computed against the
>    wrong cycle. Using the `--pitfalls-from` source, or creation order, would fix it.
> 2. Path matching over-matches with broad globs: FIX-REF-002 (a `files` metadata fix on
>    `progress.json`) matched three pitfalls whose `paths` include `docs/rite/cycles/**`, and those
>    matches then count as cross-cycle proof in `promote` (e.g. "quoted output is pasted" listed as
>    proven by FIX-REF-002). Suggest: rank `paths` matches below `tags`/title matches, and do not
>    feed path-only matches into `promote` without a confirming signal.

2. Novo issue (rascunho, não aberto):

**Título:** Reviewer turns a phase check that depends on a still-pending task into a fix

**Corpo:** In cycle refinamento, the profile's Phase 4 check used `--bass-tuning five-string`,
a preset that REF-TASK-05 was to deliver. Reviewers of REF-TASK-04 and REF-TASK-06 ran the phase
checks, found it red, and opened FIX-REF-003, which later went stale once REF-TASK-05 shipped the
preset. Suggest: when a phase check fails while tasks of the same phase are still pending, the
reviewer records it as a note (or links the check to its owning task) instead of opening a fix;
the closing task is where all phase checks must be green.

3. Comentário para https://github.com/aguilasa/rite/issues/23: quarta ocorrência (FIX-REF-002),
   agora com a regra já no `CLAUDE.md` — documentação no repositório não segurou; só a CLI segura.

### Prune

Nenhuma. `retro-suggest` sem candidatos; profile e pitfalls ainda aplicáveis.

## Applied

- Keep: entradas "Emendar files declarados…" (FIX-REF-002) e "Convenção de contrato…" (FIX-REF-001) ampliadas; nova "Check de fase só cita recurso já entregue…" (FIX-REF-003) em `docs/rite/profiles/refinamento.pitfalls.md`.
- Promote: linha "pendência vira fix ou blocked, nunca só prosa" no `CLAUDE.md` (FIX-TAB-001, FIX-REF-001).
- Report: comentário https://github.com/aguilasa/rite/issues/24#issuecomment-6477671934; comentário https://github.com/aguilasa/rite/issues/23#issuecomment-6477672284; issue nova https://github.com/aguilasa/rite/issues/25 (FIX-REF-003).
