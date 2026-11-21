---
id: FIX-STEM-006
---

# FIX-STEM-006 — Corrigir o README sobre a origem dos acordes e o que o probe confere

Origin: [STEM-TASK-02](/docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md)

## Problem

O README diz que, com a mistura como entrada, os beats **e os acordes** vêm dela. A decisão 4 e o
core somam os stems dados mais a mistura na harmonia. O README também diz que o probe confere "isto"
logo depois da frase sobre a chave de cache, e o probe não edita stem nenhum.

## Evidência

```text
$ grep -n "beats and chords come from it\|checks this end to end" README.md
323:# full mix as input (beats and chords come from it), stems given per instrument
332:using the existing caches. `scripts/probe_e2e_stems.py` checks this end to end.
```

## Root cause

O texto do README simplificou a decisão 4, e o "this" da frase sobre o probe aponta para uma afirmação que o probe não testa.

## Fix

No README: os beats vêm da mistura e os acordes, dos stems dados mais a mistura. O probe confere que o Demucs não roda, que o .gp5 é válido e que o `--stem` acerta o cache.

## Arquivos

- README.md

## Verificação

`grep -n "beats and chords come from it" README.md` vazio; `grep -n "probe_e2e_stems" README.md` descreve as três conferências.

Resultado (2026-11-21):
- `grep -n "beats and chords come from it" README.md` sai vazio (exit 1).
- A frase do probe agora lista as três conferências: Demucs pulado, .gp5 com notas, cache acertado
  no `--stem`.
- O README também cita a conversão para wav estéreo de 44,1 kHz (FIX-STEM-001).

## Execution Log

- **Closed** — commit `2a54865` (2026-11-21): docs(readme): describe where beats and chords come from with user stems
  - Files (`git show --name-status 2a54865`):
    - `M README.md`
    - `M docs/rite/cycles/entrada-stems/FIX-STEM-006.md`
