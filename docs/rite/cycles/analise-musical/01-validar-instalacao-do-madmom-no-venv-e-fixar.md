---
id: ANA-TASK-01
---

# ANA-TASK-01 — Validar instalação do madmom no venv e fixar dependência

## Goal

Existe uma forma reproduzível de instalar o madmom no venv do projeto (Python 3.11, numpy
2.x, torch atual): versão ou fork escolhido, fixado em `pyproject.toml` (ou passo documentado no
README, como o `basic-pitch --no-deps`), e o `tabgen doctor` reporta o madmom. É o risco de build
conhecido do plano (Fase 2: "validar instalação do madmom cedo"), atacado antes de qualquer código
de análise.

## Escopo

- In: testar `madmom` do PyPI (0.16.1) e o HEAD do GitHub / forks com wheels atuais no
  `.venv` (Py 3.11.15, numpy 2.4); escolher a fonte que instala e importa os processadores usados
  na fase (`DBNDownBeatTrackingProcessor`, `CNNKeyRecognitionProcessor`,
  `CNNChordFeatureProcessor`, `CRFChordRecognitionProcessor`); fixar em `pyproject.toml` ou
  documentar no README; check do madmom no `tabgen doctor`.
- Out: qualquer código de análise (TASK-03/04); trocar madmom por Beat This!/Essentia (só se
  todas as fontes falharem — aí parar e reportar ao usuário).

## Done criteria

- [ ] Instalação registrada (comando exato) sai 0 num venv limpo Python 3.11 junto com
      `pip install -e ".[dev]"`.
- [ ] `.venv/bin/python -c "from madmom.features import downbeats, key, chords; print('ok')"`
      imprime `ok`.
- [ ] `.venv/bin/tabgen doctor` lista uma linha do madmom com a versão e sai 0.
- [ ] `.venv/bin/python -c "import numpy, torch; print(numpy.__version__)"` continua igual a antes
      (madmom não rebaixa numpy nem quebra o torch) — ou o rebaixamento é registrado nas Notes com
      `.venv/bin/pytest -q` verde depois.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Risco conhecido: madmom 0.16.1 (PyPI, 2018) usa `np.float`/`np.int`, removidos no numpy ≥1.24,
e precisa de Cython no build. O HEAD do repositório CPJKU/madmom tem correções não publicadas.
Seguir o precedente do `basic-pitch` (comentário no `pyproject.toml` + passo no README) se não der
para listar como dependência normal. Pitfall herdado: gates usam `.venv/bin/`.

## Execution Log
