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

Resultado da execução: o risco se confirmou pela metade. `pip install madmom==0.16.1` falha no
build (`ModuleNotFoundError: No module named 'Cython'` — o setup.py de 2018 importa Cython sem
declará-lo como build requirement, então o build isolation do pip não o fornece); nem chegou ao
problema do `np.float`. Já o HEAD do CPJKU/madmom (commit `27f032e8947204902c675e5e341a3faf5dc86dae`,
versão `0.17.dev0`) instala limpo: tem `pyproject.toml` próprio declarando Cython/numpy no build,
compila contra numpy 2.4.6 sem rebaixá-lo (requer apenas `numpy>=1.13.4`, `scipy>=1.13`,
`mido>=1.2.6`) e todos os quatro processadores da fase importam. Não foi preciso instalar Cython
nem testar forks da comunidade. Como o HEAD resolve via `pip install -e .` sem passo extra, foi
fixado como dependência normal no `pyproject.toml` usando direct reference PEP 508 com o commit
pinado (reprodutível); o README documenta a exigência de git + compilador C no install (build a
partir do código-fonte). `tabgen doctor` ganhou o check `madmom` (essencial, com versão) em
`tabgen/core/doctor.py`, com testes dos caminhos presente/ausente. Reprodutibilidade confirmada em
venv limpo (Python 3.11.15): `pip install -e ".[dev]"` + passo do basic-pitch → madmom importa,
numpy 2.4.6 e torch intactos.

Verificação na thread principal (venv `.venv/`):

- `python -c "from madmom.features import downbeats, key, chords; print('ok')"` → `ok`
- `tabgen doctor` → `✓ madmom: madmom 0.17.dev0`, exit 0
- `python -c "import numpy, torch; print(numpy.__version__)"` → `2.4.6` (sem rebaixamento;
  torch 2.14.1+cu130 intacto)
- `pytest -q` → `54 passed` (árvore só desta task) · `ruff check .` → limpo

## Execution Log

- **Closed** — commit `1affbca` (2026-10-26): build(deps): pin madmom to CPJKU GitHub commit and add doctor check
  - Files (`git show --name-status 1affbca`):
    - `M README.md`
    - `M pyproject.toml`
    - `M tabgen/core/doctor.py`
    - `M tests/test_doctor.py`
