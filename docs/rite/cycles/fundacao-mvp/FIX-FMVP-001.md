---
id: FIX-FMVP-001
---

# FIX-FMVP-001 — Corrigir padrão .tabgen/ no .gitignore (comentário inline quebra o match)

Origin: [FMVP-TASK-02](/docs/rite/cycles/fundacao-mvp/02-implementar-contratos-de-estagio-e-cache-em.md)

## Problem

A entrada do `.gitignore` que deveria ignorar o diretório de cache `.tabgen/` (introduzido
pela FMVP-TASK-02) carrega um comentário inline; o git trata a linha inteira como padrão, então
`.tabgen/` **não** é ignorado. Rodar o tabgen sobre áudio dentro de um repositório git deixa o
cache aparecendo como untracked, contra a intenção declarada.

## Evidência

```text
$ grep -n "tabgen" .gitignore
19:.tabgen/        # cached intermediate stage results
$ git check-ignore -v ".tabgen/foo.json"; echo "exit=$?"
exit=1
```

(`exit=1` = não ignorado; esperado `exit=0` com a linha 19 como fonte.)

## Root cause

Hipótese (mecanismo provado, intenção não): autor assumiu que gitignore aceita comentário no fim
da linha; git só reconhece `#` no início da linha, então o texto do comentário vira parte do
padrão e nunca casa. Defeito pré-existente do commit de scaffold `6f4f034`, exposto pelo cache
`.tabgen/` da FMVP-TASK-02; não introduzido por `db3c462`.

## Fix

Em `.gitignore` linha 19, mover o comentário para linha própria: uma linha
`# cached intermediate stage results` seguida de uma linha só com `.tabgen/`. Arquivo escrito à
mão, não gerado (`sh "$RITE_HOME/bin/rite" guard .gitignore` → not blocked), então a edição vai
direto nele.

## Arquivos

- `.gitignore`

## Verificação

```text
$ git check-ignore -q ".tabgen/foo.json"; echo "exit=$?"
```

Hoje `exit=1` (vermelho); depois do fix deve ser `exit=0` (verde).

Medido após o fix (2026-10-26):

```text
$ git check-ignore -q ".tabgen/foo.json"; echo "exit=$?"
exit=0
```

## Execution Log

- 2026-10-26 — Triagem (`rite reproduce FIX-FMVP-001`): REPRODUCED.

  ```text
  $ grep -n "tabgen" .gitignore
  19:.tabgen/        # cached intermediate stage results
  $ git check-ignore -v ".tabgen/foo.json"; echo "exit=$?"
  exit=1
  ```
- **Closed** — commit `215ae9a` (2026-10-26): fix(gitignore): move inline comment off .tabgen/ line so pattern matches
  - Files (`git show --name-status 215ae9a`):
    - `M .gitignore`
