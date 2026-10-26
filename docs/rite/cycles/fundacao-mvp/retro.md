# Retro — fundacao-mvp

Date: 2026-10-26

## Numbers

Fonte: `rite stats fundacao-mvp --json`.

- Tarefas: 8 (8 done, 0 pending/blocked/skipped).
- Fixes: 7 (7 done, 0 stale); severidade: 0 critical, 2 high, 1 medium, 4 low.
- Fixes por tarefa: 0,88. Por fase: Fase 0 — 4 tarefas / 3 fixes; Fase 1 — 4 tarefas / 4 fixes.
- Origem: FMVP-TASK-08 = 2; FIX-FMVP-001, FMVP-TASK-02, FMVP-TASK-03, FMVP-TASK-05, FMVP-TASK-07 = 1 cada.
- Latência de review: mediana 0 dias (8 revisadas).
- Tempo ativo: tarefas total 2830 s (mediana 347,5 s); fixes total 17459 s (mediana 264 s, máx 8255 s).

## Root-cause groups

| Grupo | Qtd | Tipo | Fixes |
|---|---|---|---|
| Artefato localizado/validado por caminho errado ou compartilhado (cwd em vez do cache de modelos; cache hit validado só por existência) | 2 | engineering | FIX-FMVP-002, FIX-FMVP-004 |
| Números publicados sem probe versionado ou não reconciliados com a medição (Notes da task, README) | 2 | engineering | FIX-FMVP-005, FIX-FMVP-006 |
| Comandos de gate assumindo venv ativado | 1 | engineering | FIX-FMVP-003 |
| Sintaxe de `.gitignore` (comentário inline vira parte do padrão) | 1 | engineering | FIX-FMVP-001 |
| Arquivo fora dos `files` declarados commitado sem emendar o item | 1 | bookkeeping | FIX-FMVP-007 |

Totais: engineering 6, bookkeeping 1.

## Proposals

### Keep in next profile

Entradas para `docs/rite/profiles/fundacao-mvp.pitfalls.md` (copiado pelo `/rite:new-cycle --pitfalls-from`):

```markdown
### Cache hit valida identidade do artefato, não só existência
- tags: cache, stems, separation
- paths: tabgen/core/**
- proven by: FIX-FMVP-004 (2026-10-26)
- rule: quando o artefato cacheado vive em caminho compartilhado entre inputs, gravar identidade (tamanho + mtime_ns ou hash) no payload e comparar no hit.

### Checagem de recurso mede onde o recurso vive
- tags: doctor, disk, paths
- paths: tabgen/core/doctor.py
- proven by: FIX-FMVP-002 (2026-10-26)
- rule: nunca usar cwd como default para checar disco/cache; resolver o diretório real (ex.: `torch.hub.get_dir()`) e medir o ancestral existente mais próximo.

### Números em Notes/README exigem probe versionado
- tags: verification, numbers, readme, e2e
- paths: README.md, docs/rite/cycles/**, scripts/**
- proven by: FIX-FMVP-005, FIX-FMVP-006 (2026-10-26)
- rule: todo número publicado vem com o comando versionado que o gera (incl. geração da amostra) e afirma só fatos estáveis; após um e2e real, atualizar no mesmo item os documentos que citavam estimativas.

### Gates chamam binários do venv
- tags: gates, venv, tooling
- paths: docs/rite/profiles/*.md, rite.toml
- proven by: FIX-FMVP-003 (2026-10-26)
- rule: comandos de gate usam `.venv/bin/<tool>`, pois `rite gates` roda em bash limpo sem venv no PATH.

### .gitignore sem comentário inline
- tags: gitignore
- paths: .gitignore
- proven by: FIX-FMVP-001 (2026-10-26)
- rule: comentário em `.gitignore` só em linha própria; validar com `git check-ignore -v <caminho>`.

### Emendar files declarados antes de commitar fora do escopo
- tags: bookkeeping, files, scope
- paths: docs/rite/cycles/**
- proven by: FIX-FMVP-007 (2026-10-26)
- rule: ao tocar arquivo fora dos `files` do item, rodar `rite set <ID> --files ...` antes do `rite finish`.
```

### Promote to rite.toml / CLAUDE.md

Nenhuma regra provada em dois ciclos (este é o primeiro; sem retros anteriores).

Candidato com evidência de um ciclo só (exceção a decidir): mover os gates para `rite.toml`
`[gates].global` (`.venv/bin/pytest -q`, `.venv/bin/ruff check .`). Motivo: gates do profile não
passam para o próximo ciclo (profile novo nasce esqueleto), e o defeito de FIX-FMVP-003 voltaria.

### Rite issues (plugin)

**Título:** `rite finish` registra "Outside declared files" mas não oferece emendar `files`, e o review abre fix só de bookkeeping

**Corpo:** No ciclo fundacao-mvp (tabgen), `rite finish` da FMVP-TASK-08 logou
`Outside declared files (README.md): pyproject.toml`, e as Notes justificavam a divergência. O
review seguinte abriu FIX-FMVP-007 apenas para rodar `rite set FMVP-TASK-08 --files
README.md,pyproject.toml` — um fix de bookkeeping inteiro (triagem, reproduce, commit, close) para
um ajuste que o `finish` já detectara. Sugestão: `rite finish` aceitar `--amend-files` (ou
perguntar) quando detecta arquivos fora do escopo, ou o reviewer tratar divergência já logada e
justificada como nota, não fix.

### Prune

- Profile § Phase-specific checks, Fase 0: troca `pytest -q` e `ruff check .` nus por
  `.venv/bin/pytest -q` e `.venv/bin/ruff check .` (mesma causa de FIX-FMVP-003; sinalizado nas
  Notas desse fix).
- Profile em 3530 bytes; nada a mover para pitfalls. Hot files/decisões não tocados por fix, mas
  ainda válidos para o próximo ciclo — manter.

## Applied

- Keep: 6 pitfalls gravados em `docs/rite/profiles/fundacao-mvp.pitfalls.md` (FIX-FMVP-001..007).
- Report: issue aberta — https://github.com/aguilasa/rite/issues/23 (FIX-FMVP-007).
- Não aplicados (decisão do usuário): Promote gates globais; Prune checks da Fase 0.
