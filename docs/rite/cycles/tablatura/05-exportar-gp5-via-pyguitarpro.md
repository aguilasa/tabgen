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

- [ ] Teste: `TabScore` sintética exportada e relida com `guitarpro.parse()` preserva, por nota,
      corda, casa e posição (compasso, beat); afinação e BPM das faixas batem.
- [ ] Teste: cada compasso relido soma exatamente a duração da fórmula de compasso (sem compasso
      incompleto ou estourado), incluindo um caso com tercina e um com nota ligada entre compassos.
- [ ] `.venv/bin/python -c "import guitarpro; print(guitarpro.__version__)"` imprime a versão fixada.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Abrir no TuxGuitar fica para a verificação manual da TASK-08. Licença LGPL de PyGuitarPro já
aceita no plano, seção 4.

## Execution Log
