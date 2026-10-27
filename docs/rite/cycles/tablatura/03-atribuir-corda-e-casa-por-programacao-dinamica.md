---
id: TAB-TASK-03
---

# TAB-TASK-03 — Atribuir corda e casa por programação dinâmica

## Goal

Existe `tabgen/core/fretting/`: dado `NoteEvents` (e opcionalmente os acordes do
`AnalysisResult`), atribui a cada nota uma (corda, casa) por programação dinâmica — estado =
posição da mão; custo = deslocamento + abertura de dedos + penalidade de corda solta fora de
contexto + bônus por forma do acorde vigente — com afinação, nº de cordas, capo e casa máxima
configuráveis. Notas fora da tessitura são relatadas, não descartadas em silêncio.

## Escopo

- In: candidatos (corda, casa) por pitch; agrupamento de notas simultâneas (acorde = uma corda por
  nota); DP/Viterbi sobre a sequência; prior de acordes do estágio 2; presets guitarra 6 / baixo 4;
  testes com escalas e acordes conhecidos. Ler tuttut/tayuya como referência, sem dependência.
- Out: ML (TabCNN/TART); técnicas; afinações exóticas além de configurar `tuning_midi` (Fase 4).

## Done criteria

- [ ] Teste: escala de Lá menor pentatônica na 5ª casa (pitches 57,60,62,64,67,69,72,74,76,79,81)
      sai toda entre as casas 5 e 8 (box position), sem saltos >4 casas entre notas vizinhas.
- [ ] Teste: notas simultâneas nunca compartilham corda; tríade de Dó maior aberta
      (48,52,55,60,64) com acorde `C:maj` vigente sai na forma aberta (casas 3,2,0,1,0).
- [ ] Teste: afinação drop D (`[38,45,50,55,59,64]`) coloca o pitch 38 na corda 6 casa 0; pitch
      fora da tessitura aparece na lista de não atribuídas.
- [ ] Teste: baixo 4 cordas (`[28,33,38,43]`) atribui todas as notas de uma linha em E menor.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Coração do valor próprio do projeto (plano, Estágio 5). Custo e pesos ficam como parâmetros
nomeados para ajuste na Fase 4; registrar nas Notes os pesos escolhidos e por quê.

## Execution Log
