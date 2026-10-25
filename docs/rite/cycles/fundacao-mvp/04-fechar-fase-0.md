---
id: FMVP-TASK-04
---

# FMVP-TASK-04 — Fechar Fase 0

## Goal

A Fase 0 (fundação) está verificada de ponta a ponta: pacote instalável, contratos com cache,
`tabgen doctor` funcional, gates verdes e checks da fase executados.

## Escopo

- In: re-executar gates e os checks da Fase 0 do profile; corrigir pequenas pendências de
  integração entre as tarefas 01–03; atualizar README com instruções de instalação reais.
- Out: qualquer funcionalidade nova.

## Done criteria

- [ ] Em venv limpa: `pip install -e ".[dev]"` → `tabgen --version` → `tabgen doctor` exit 0.
- [ ] `pytest -q` e `ruff check .` verdes.
- [ ] `grep -rE "import typer|import rich|print\(" tabgen/core/` vazio.
- [ ] README descreve instalação e doctor (seções testáveis copiando/colando os comandos).

## Notes

## Execution Log
