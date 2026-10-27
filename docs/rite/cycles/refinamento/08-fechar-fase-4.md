---
id: REF-TASK-08
---

# REF-TASK-08 — Fechar Fase 4

## Goal

A Fase 4 está verificada: técnicas aparecem no .gp5 de uma música real escolhida pelo usuário
e abrem no TuxGuitar; baixo de 5 cordas e violão nylon/aço funcionam pela CLI; o relatório de
avaliação existe com números reproduzíveis; checks e gates da fase verdes; README atualizado
(técnicas, novos presets, números de avaliação e limitações).

## Escopo

- In: rodada e2e com música real; conferência manual das técnicas no TuxGuitar pelo usuário;
  checks da Fase 4; README; venv limpa; probes e2e.
- Out: Fase 5 (web/desktop).

## Done criteria

- [ ] `.venv/bin/tabgen export <música real>.mp3 -o <música>.gp5` sai 0; usuário confirma no
      TuxGuitar que bends/slides/hammer-ons aparecem (registrado nas Notes).
- [ ] `.venv/bin/python scripts/probe_e2e_export.py` e `scripts/probe_e2e_sample.py` saem 0.
- [ ] Todos os checks da Fase 4 do profile passam.
- [ ] Venv limpa: instalação documentada sai 0 e `.venv/bin/pytest -q` verde.
- [ ] README tem seção de técnicas, presets novos e tabela de avaliação com o comando que a gera.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-FMVP-006): números medidos vão ao README neste mesmo item.

## Execution Log
