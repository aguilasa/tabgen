---
id: FIX-UI-008
---

# FIX-UI-008 — Rastrear em fix real o probe dos números e2e da UI-TASK-06

Origin: [UI-TASK-06](/docs/rite/cycles/interface-desktop/06-implementar-painel-de-opcoes-de-geracao.md)

## Problem

A UI-TASK-06 fechada diz "Números e2e por comando inline, sem probe (ver FIX-UI-007)", mas a
FIX-UI-007 cobre somente o critério 2 da UI-TASK-05 (export MusicXML do cache); nenhum fix do
ciclo rastreia o probe dos números e2e da UI-TASK-06 (geração drop-d+capo2+nylon via worker,
troca de transcriber no nível do worker, tempo do cache da tablatura). A regra promovida do
CLAUDE.md exige que pendência de tarefa fechada vire fix pela CLI, nunca fique só em prosa.

## Evidência

```text
$ grep -c "UI-TASK-06" docs/rite/cycles/interface-desktop/FIX-UI-007.md
0

$ grep -n "ver FIX-UI-007" docs/rite/cycles/interface-desktop/06-implementar-painel-de-opcoes-de-geracao.md
69:  pureza do core vazio. Números e2e por comando inline, sem probe (ver FIX-UI-007).

$ grep -n "critério 2 da UI-TASK-05" docs/rite/cycles/interface-desktop/FIX-UI-007.md
13:O critério 2 da UI-TASK-05 (export MusicXML a partir do gp5 reusa o cache em <5 s e reabre no music21) foi medido por comando inline e pelo cronômetro da UI; `scripts/probe_e2e_worker.py` não cobre esse caminho, e a regra do CLAUDE.md exige probe versionado para número e2e.
```

## Root cause

Hipótese (não provada): ao fechar a UI-TASK-06 em lote com a UI-TASK-05, o fix já aberto pela
onda anterior (FIX-UI-007) foi citado como cobertura sem ampliar seu escopo.

## Fix

Este fix é a cobertura que faltava: estender `scripts/probe_e2e_worker.py` (ou o probe que a
FIX-UI-007 entregar) para cobrir os números e2e da UI-TASK-06 reproduzíveis do HEAD —
geração drop-d+capo2+nylon via worker com reabertura `guitarpro.parse` (`[64, 59, 55, 50, 45,
38] 2 24`), troca de transcriber invalidando só os estágios de transcrição, e cache da
tablatura <5 s.

## Arquivos

- scripts/probe_e2e_worker.py
- docs/rite/cycles/interface-desktop/06-implementar-painel-de-opcoes-de-geracao.md

## Verificação

```text
$ grep -c "UI-TASK-06" docs/rite/cycles/interface-desktop/FIX-UI-00*.md
```

Hoje 0 em todos; este fix existe para isso — depois dele o probe roda verde do HEAD:
`.venv/bin/python scripts/probe_e2e_worker.py` cobrindo os três números acima.

## Execution Log

- 2026-10-29 — Triagem inline (`rite reproduce --all --cycle interface-desktop`): REPRODUCED.
  `grep -c "UI-TASK-06" FIX-UI-007.md` → `0`; `grep -n "ver FIX-UI-007"` no doc da UI-TASK-06
  → linha 86 (Evidência gravou 69; doc cresceu, conteúdo idêntico); FIX-UI-007 segue restrito
  ao critério 2 da UI-TASK-05. Nenhum fix cobre os números e2e da UI-TASK-06.
- 2026-10-29 — Fix (agente executor): `scripts/probe_e2e_worker.py` passou de 2 para 5 runs no
  mesmo tempdir — cold/warm com `transcriber: basic-pitch` explícito, troca para `riley`
  (invalidação por estágio: primeiro pct 100.0 = hit, <100.0 = re-run), geração
  drop-d+capo2+nylon com reabertura `guitarpro.parse` e warm das opções; linha 86 do doc da
  UI-TASK-06 agora cita este fix e o escopo real da FIX-UI-007. Verificação na árvore do
  commit (FIX-UI-009 em stash): `.venv/bin/python scripts/probe_e2e_worker.py` → exit 0,
  `PASS: five worker runs exit 0 with NDJSON-only stdout and stage order following
  _tablature_stages + export; cold (basic-pitch) cache_hit=false in 13.8 s (not asserted),
  warm cache_hit=true in 0.21 s (< 5 s); transcriber switch to riley: cache_hit=false,
  analysis + transcription:bass first pct 100.0, transcription:guitar re-ran, in 4.2 s (not
  asserted); drop-d + capo 2 + nylon .gp5 reopened as [64, 59, 55, 50, 45, 38] 2 24 in 0.2 s
  (not asserted); warm options cache_hit=true in 0.21 s (< 5 s).`; `grep -n "FIX-UI-008"` no
  doc 06 → linha 86; `rite gates --id FIX-UI-008` → passed (0 gates). Agente mediu também
  `.venv/bin/pytest -q` → 260 passed e `.venv/bin/ruff check .` → All checks passed.
