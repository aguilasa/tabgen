---
id: TAB-TASK-05
---

# TAB-TASK-05 — Exportar .gp5 via PyGuitarPro

## Goal

Existe `tabgen/core/export/gp5.py`: converte uma ou mais `TabScore` (guitarra, baixo) num
arquivo `.gp5` via PyGuitarPro — uma faixa por instrumento com afinação e capo, BPM, armadura,
compassos com as notas na corda/casa e duração quantizadas, e símbolos de acorde anotados.

## Escopo

- In: dependência `PyGuitarPro` fixada no `pyproject.toml` (verificar instalação em Py 3.11);
  mapeamento subdivisão → `Duration` (incl. tercinas e ligaduras quando a nota cruza compasso);
  pausas preenchendo o compasso; faixas guitarra e baixo; chord diagrams/texto por compasso.
- Out: técnicas (bend/slide/hammer — Fase 4); GPX/GP6+.

## Done criteria

- [x] Teste: `TabScore` sintética exportada e relida com `guitarpro.parse()` preserva, por nota,
      corda, casa e posição (compasso, beat); afinação e BPM das faixas batem.
- [x] Teste: cada compasso relido soma exatamente a duração da fórmula de compasso (sem compasso
      incompleto ou estourado), incluindo um caso com tercina e um com nota ligada entre compassos.
- [x] `.venv/bin/python -c "import importlib.metadata; print(importlib.metadata.version('pyguitarpro'))"`
      imprime a versão fixada.
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Abrir no TuxGuitar fica para a verificação manual da TASK-08. Licença LGPL de PyGuitarPro já
aceita no plano, seção 4.

Dependência fixada: `pyguitarpro==0.11` (última versão; o writer gp5 é sensível a mudanças de
layout do modelo, por isso o pin exato).

**Critério da versão (reescrito para ser verificável)**: o comando original falhava porque o
pacote PyGuitarPro não expõe `__version__` em nenhuma versão publicada (verificado em 0.11 e
0.10.2): `.venv/bin/python -c "import guitarpro; print(guitarpro.__version__)"` →
`AttributeError: module 'guitarpro' has no attribute '__version__'`. Critério ajustado para o
equivalente via `importlib.metadata`, que imprime `0.11` (comando rodado na verificação abaixo).

Decisões de design:

- **Numeração de cordas**: convenção de guitarrista (corda 1 = mais aguda), igual ao módulo de
  fretting e ao `GuitarString` do PyGuitarPro; afinação gravada invertendo `tuning_midi`
  (low-to-high → corda 1..N) e capo no `Track.offset` do GP5. A docstring de `TabNote` em
  `models.py` já foi corrigida pelo FIX-TAB-001 (commit 909100e) — nada a reconciliar.
- **Tercinas**: `TabNote` não carrega a resolução da grade, então `export_gp5` aceita
  `beat_grids` — por score, lista paralela a `events` com o `subdivisions_in_beat` de cada nota
  (4 reto / 3 tercina, espelhando `QuantizedNote.subdivisions_in_beat`). JSON-trivial (lista de
  listas de int); entradas ausentes caem em `default_subdivisions_in_beat=4`. A TASK-07 monta
  `beat_grids` a partir das `QuantizedNote` sobreviventes ao fretting (cuidado com notas
  descartadas em `unassigned`: as listas devem ficar paralelas aos `events` finais).
- **Ligaduras e pausas**: nota que cruza compasso (ou sem duração GP única) é partida em beats
  ligados (`NoteType.tie`); durações/pausas arbitrárias são decompostas gulosamente em átomos
  GP (inteira..fusa de 128, pontuadas e tercinas), e cada compasso é completado com pausas até
  somar exatamente a fórmula.
- **Polifonia**: uma voz por faixa; onsets simultâneos viram um beat (acorde) com a menor
  duração do grupo, e nota sobreposta é truncada no próximo onset — convenção padrão de
  tablatura monofônica por voz; voz 2 fica vazia (formato GP5 exige duas).
- **Acordes**: rótulo Harte como `Chord.name` (texto, sem diagrama) no primeiro beat do
  compasso; `"N"` não é anotado. Armadura mapeada de `"<tônica> <modo>"` para
  `KeySignature` (gravada nos headers; o `song.key` do GP5 não sobrevive ao round-trip),
  com fallback C maior para tons sem enarmônico suportado.
- **Anacruse**: compassos ≤ 0 (pickup da quantização) deslocam a grade para começar no
  compasso 1.

Verificação (2026-10-27, thread principal, árvore do commit):

- `.venv/bin/pytest -q` → `110 passed, 11 warnings in 9.54s`
- `.venv/bin/ruff check .` → `All checks passed!`
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1)
- `.venv/bin/python -c "import importlib.metadata; print(importlib.metadata.version('pyguitarpro'))"`
  → `pyguitarpro 0.11`; pin em `pyproject.toml`: `"pyguitarpro==0.11"`

## Execution Log

- **Closed** — commit `dd7a59f` (2026-10-27): feat(export): write TabScores as Guitar Pro 5 files via PyGuitarPro
  - Files (`git show --name-status dd7a59f`):
    - `M docs/rite/cycles/tablatura/05-exportar-gp5-via-pyguitarpro.md`
    - `M pyproject.toml`
    - `A tabgen/core/export/gp5.py`
    - `A tests/test_gp5_export.py`
- **Reviewed** (2026-10-27) at `c229551`: FIX-TAB-003
