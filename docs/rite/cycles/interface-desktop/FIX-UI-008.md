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
