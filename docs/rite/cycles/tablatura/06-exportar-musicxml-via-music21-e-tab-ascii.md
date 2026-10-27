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

- [x] Teste: MusicXML exportado relido por `music21.converter.parse` tem o mesmo nº de compassos,
      as mesmas alturas na mesma ordem e a armadura correta.
- [x] Teste: ASCII de golden pequeno (riff de 1 compasso, guitarra) bate byte a byte com o
      esperado versionado em `tests/`.
- [x] Teste: ASCII de baixo tem 4 linhas de corda por sistema.
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

MusicXML e ASCII são secundários (plano, compatibilidade de formatos); o golden ASCII fixa o
formato visível.

Implementação:

- `music21==10.5.1` fixado em `pyproject.toml` (não estava instalado; versão mais recente do
  PyPI). `music21.configure` nunca é chamado.
- `tabgen/core/export/musicxml.py`: `export_musicxml(scores, output_path, beat_grids=None,
  default_subdivisions_in_beat=4, title="")`, espelhando a assinatura do exporter gp5 (mesma
  convenção de `beat_grids`, mesma exigência de time signature única, mesmo deslocamento de
  anacruse, mesma truncagem de sobreposições e split com ligaduras em fronteiras de compasso).
  Tercinas viram durações de tuplet reais do music21 (quarterLength fracionário, p.ex. 1/3).
  Pauta + tablatura simplificada: as notas carregam a altura soante (corda + traste + capo) e
  indicações técnicas de corda/traste (`StringIndication`/`FretIndication`) em notas simples;
  um pentagrama TAB dedicado ficou fora (engraving fino, fora do escopo). Símbolos de acorde
  Harte → figura music21 (maj/min/7/maj7/min7/dim/aug/sus2/sus4; `N` e rótulos desconhecidos
  são pulados). Armadura via `music21.key.Key`, fallback Dó maior como no gp5.
- `tabgen/core/export/ascii_tab.py`: `render_ascii_tab(...) -> str` e
  `export_ascii_tab(scores, output_path, beat_grids=None, default_subdivisions_in_beat=4,
  measures_per_line=4)`. Formato próprio: cabeçalho (instrumento, afinação low-to-high em
  notação científica, capo quando > 0, BPM, tom quando conhecido, fórmula de compasso),
  sistemas com quebra a cada `measures_per_line` (padrão 4) compassos, uma linha por corda
  (corda 1 no topo: 6 linhas para guitarra, 4 para baixo), células de largura fixa por
  subdivisão (traste alinhado por compasso, preenchido com `-`), linha de acordes alinhada por
  compasso quando há rótulos. Tercinas são achatadas na grade reta: coluna =
  `round(s * cells / grid)`; só onsets são desenhados (durações não aparecem), colisão na
  mesma célula/corda fica com o evento posterior — tudo documentado no docstring do módulo.
- Golden versionado em `tests/golden/ascii_guitar_riff.txt` (riff de 1 compasso, guitarra),
  gerado pelo exporter e conferido visualmente; o teste compara byte a byte.

Verificação (2026-10-27, thread principal, árvore do commit):

- `.venv/bin/pytest -q tests/test_musicxml_export.py tests/test_ascii_tab.py` → `9 passed in 0.25s`
- `.venv/bin/pytest -q` → `119 passed, 11 warnings in 9.47s`
- `.venv/bin/ruff check .` → `All checks passed!`
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1)
- pin em `pyproject.toml`: `"music21==10.5.1"` (não estava instalado antes, apesar do README citar)
- `rite sweep --terms export_musicxml,export_ascii_tab,music21` → nenhuma menção desatualizada

## Execution Log
