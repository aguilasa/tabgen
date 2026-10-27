---
id: REF-TASK-05
---

# REF-TASK-05 — Suportar baixo de 5 cordas e violão nylon ou aço

## Goal

O `tabgen export` suporta baixo de 5 cordas (preset `B0 E1 A1 D2 G2`, fretting e .gp5 com 5
cordas) e escolha do violão: `--guitar-type electric|nylon|steel` define o programa GM da faixa
(.gp5/MIDI/MusicXML) e limites de fretting próprios (casa máxima do violão nylon menor).

## Escopo

- In: preset `five-string` em `--bass-tuning`; `FrettingConfig` por tipo de instrumento; programa
  GM 24 (nylon), 25 (aço), 27/29 (elétrica) mapeado nos exportadores; ASCII com 5 linhas no baixo.
- Out: afinações exóticas além de notas explícitas (já suportadas por `--tuning`); 7 cordas.

## Done criteria

- [ ] Teste: linha de baixo com B0 (pitch 23) é atribuída na corda 5 casa 0 com o preset de 5
      cordas; com o de 4 cordas aparece como não atribuída.
- [ ] Teste: .gp5 relido tem faixa de baixo com 5 cordas e afinação correta.
- [ ] Teste: `--guitar-type nylon` gera faixa com programa GM 24 no .gp5 e no MIDI.
- [ ] Teste: ASCII de baixo de 5 cordas tem 5 linhas por sistema.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Afinações alternativas e capo já existem (`--tuning`, `--bass-tuning`, `--capo`, Fase 3); esta
tarefa cobre só o que falta do item do plano.

## Execution Log
