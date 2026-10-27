---
id: REF-TASK-04
---

# REF-TASK-04 — Exportar técnicas em gp5, MusicXML e ASCII e ligar no pipeline

## Goal

As técnicas saem nos formatos: .gp5 grava bend (`BendEffect`), slide e hammer-on/pull-off
(`NoteEffect`) via PyGuitarPro; MusicXML grava as notações equivalentes (`bend`, `slide`/`glissando`,
`hammer-on`/`pull-off`); a tab ASCII usa as marcas usuais (`7b9`, `5/7`, `7\5`, `5h7`, `7p5`).
`run_tablature` aplica as detecções (TASK-02/03) e `tabgen export` passa a gerá-las, com flag
para desligar (`--no-techniques`).

## Escopo

- In: mapeamento técnica → efeito em cada exportador; ligação no pipeline após fretting; versão
  de cache do estágio de tablatura incluindo o conjunto de técnicas; golden ASCII novo; atualizar
  `scripts/probe_e2e_export.py` só com fatos estáveis.
- Out: técnicas além das da TASK-01.

## Done criteria

- [ ] Teste: `TabScore` com as quatro técnicas exportada em .gp5 e relida com `guitarpro.parse()`
      preserva cada efeito na nota correta.
- [ ] Teste: MusicXML relido pelo music21 contém as notações técnicas nas notas correspondentes.
- [ ] Teste: golden ASCII versionado em `tests/golden/` com bend, slide, hammer e pull bate byte a
      byte.
- [ ] `--no-techniques` gera saída sem nenhum efeito (teste de CLI com funções injetadas).
- [ ] `.venv/bin/python scripts/probe_e2e_export.py` sai 0.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Hot files: `tabgen/core/pipeline.py`, `tabgen/cli/main.py`, `tabgen/core/export/*`. Regra do
`CLAUDE.md`: conferir `files` contra o diff antes do `rite finish`.

## Execution Log
