---
id: UI-TASK-08
---

# UI-TASK-08 — Fechar Fase 5

## Goal

A Fase 5 está verificada: fluxo completo no app com música real escolhida pelo usuário —
abrir, gerar com opções, acompanhar progresso, ver resultados e exportar .gp5 que abre no
TuxGuitar — com confirmação manual do usuário; checks e gates da fase verdes; README raiz
atualizado (seção do app desktop com screenshot).

## Escopo

- In: rodada e2e com música real no app (frio e quente); confirmação do usuário (TuxGuitar);
  checks da Fase 5 do profile; README raiz; probes e suíte Python intactos.
- Out: distribuição pública dos pacotes; v2.

## Done criteria

- [ ] Fluxo completo com música real no app: frio e quente, tempos anotados nas Notes com como
      foram medidos; usuário confirma o .gp5 no TuxGuitar (registrado nas Notes).
- [ ] Todos os checks da Fase 5 do profile passam.
- [ ] `.venv/bin/python scripts/probe_e2e_export.py` e `scripts/probe_e2e_sample.py` saem 0.
- [ ] README raiz tem a seção do app desktop (como rodar/instalar) com screenshot.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-FMVP-006): números medidos vão ao README neste mesmo item.

## Execution Log
