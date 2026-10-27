---
id: TAB-TASK-02
---

# TAB-TASK-02 — Quantizar notas na grade de beats

## Goal

Existe `tabgen/core/export/quantize.py` (ou módulo próprio em `core/`): projeta onset/offset de
cada `Note` na grade de beats/downbeats do `AnalysisResult`, com resolução de semicolcheia por
padrão e tercinas detectadas por ajuste, devolvendo posição (compasso, tempo, subdivisão) e
duração em subdivisões. É a etapa que define se a tab "parece certa" (plano, Estágio 6).

## Escopo

- In: grade de subdivisões entre beats consecutivos (andamento variável respeitado); compasso a
  partir dos downbeats; snap de onset e duração mínima de 1 subdivisão; detecção de tercina por
  erro de ajuste menor; notas antes do primeiro downbeat (anacruse) tratadas; testes com grades
  sintéticas.
- Out: fretting (TASK-03); fórmula de compasso variável (Fase 4).

## Done criteria

- [ ] Teste: notas exatamente em semicolcheias a 120 BPM 4/4 (com jitter aleatório ±20 ms, seed
      fixa) voltam nas posições originais (compasso, tempo, subdivisão) em 100% dos casos.
- [ ] Teste: três notas igualmente espaçadas num beat são quantizadas como tercina, não como
      semicolcheias.
- [ ] Teste: grade com andamento variável (beats com intervalos crescentes) mantém cada nota no
      beat correto.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado: afirmar fatos estáveis (posições), não contagens frágeis. Referência para
comparação: MuseScore CLI (plano, seção 6) — opcional.

## Execution Log
