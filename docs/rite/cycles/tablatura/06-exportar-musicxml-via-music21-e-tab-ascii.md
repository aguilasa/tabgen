---
id: TAB-TASK-06
---

# TAB-TASK-06 — Exportar MusicXML via music21 e tab ASCII

## Goal

Existe export secundário: MusicXML via music21 (pauta + tablatura, armadura, BPM, símbolos de
acorde) e tab ASCII própria (6/4 linhas por instrumento, casas alinhadas por compasso) a partir
da mesma `TabScore`.

## Escopo

- In: dependência `music21` fixada; `tabgen/core/export/musicxml.py` e
  `tabgen/core/export/ascii_tab.py`; ASCII com cabeçalho (afinação, BPM, tom) e quebra de linha por
  N compassos.
- Out: import em TuxGuitar (plano: não confirmado); engraving fino.

## Done criteria

- [ ] Teste: MusicXML exportado relido por `music21.converter.parse` tem o mesmo nº de compassos,
      as mesmas alturas na mesma ordem e a armadura correta.
- [ ] Teste: ASCII de golden pequeno (riff de 1 compasso, guitarra) bate byte a byte com o
      esperado versionado em `tests/`.
- [ ] Teste: ASCII de baixo tem 4 linhas de corda por sistema.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

MusicXML e ASCII são secundários (plano, compatibilidade de formatos); o golden ASCII fixa o
formato visível.

## Execution Log
