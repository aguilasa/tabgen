---
id: FMVP-TASK-08
---

# FMVP-TASK-08 — Fechar Fase 1

## Goal

A Fase 1 está verificada com música real: pipeline separa + transcreve uma gravação comercial
de teste de ponta a ponta na GPU, cache funciona entre execuções, gates e checks da fase
verdes, README atualizado com o uso real do MVP.

## Escopo

- In: rodada e2e com música real (escolhida pelo usuário), medição de tempos por estágio
  (separação, transcrição) registrada no Execution Log, revisão dos checks da Fase 1 do
  profile, atualização do README (uso, exemplos, tempos esperados).
- Out: melhorias de qualidade de transcrição (Fase 4); novos recursos.

## Done criteria

- [ ] `tabgen transcribe <música real>.mp3` completa sem erro na GPU; tempos por estágio
      anotados no Execution Log.
- [ ] `.mid` resultante abre no TuxGuitar (verificação manual confirmada pelo usuário ou
      screenshot anexado).
- [ ] Todos os checks da Fase 1 do profile passam.
- [ ] `pytest -q` e `ruff check .` verdes em venv limpa.

## Notes

## Execution Log
