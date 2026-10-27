---
id: REF-TASK-03
---

# REF-TASK-03 — Detectar hammer-on e pull-off por onsets fracos

## Goal

Existe heurística de legato: uma nota cujo ataque é fraco (velocity/amplitude bem abaixo da
nota anterior), que começa logo ao fim da anterior e fica na mesma corda vira hammer-on (pitch
sobe) ou pull-off (pitch desce), preenchendo a técnica da `TabNote` (plano, Fase 4).

## Escopo

- In: critérios nomeados (razão de amplitude, gap máximo, mesma corda, intervalo ≤ 5 casas);
  aplicada depois do fretting; testes sintéticos.
- Out: tapping, trinados como técnica própria; classificador de ML.

## Done criteria

- [ ] Teste: casa 5 forte seguida de casa 7 com amplitude 30% e gap 0 na mesma corda vira
      hammer-on; 7 → 5 nas mesmas condições vira pull-off.
- [ ] Teste: mesma sequência com segunda nota forte, com gap > limiar ou em outra corda não vira
      legato.
- [ ] Teste: primeira nota de um compasso após pausa nunca é marcada como legato.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Heurística sem ground truth local; a qualidade real é medida pelo harness (TASK-06) se o dataset
tiver anotação de técnica (EGDB/Guitar-TECHS) — registrar se não tiver.

## Execution Log
