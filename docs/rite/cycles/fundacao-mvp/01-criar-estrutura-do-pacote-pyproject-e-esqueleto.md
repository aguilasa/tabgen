---
id: FMVP-TASK-01
---

# FMVP-TASK-01 — Criar estrutura do pacote, pyproject e esqueleto da CLI

## Goal

Existe um pacote Python instalável (`pip install -e .`) com a estrutura em camadas do plano
(seção 2): `tabgen/core/` (biblioteca pura) e `tabgen/cli/` (typer), mais tooling de
desenvolvimento (pytest, ruff) e um comando `tabgen --version` funcionando.

## Escopo

- In: `pyproject.toml` (deps base: typer, rich; dev: pytest, ruff), pacote `tabgen/` com
  subpacotes vazios `core/{separation,analysis,transcription,fretting,export}` e `cli/`,
  `tabgen/cli/main.py` com typer app e `--version`, `tests/` com um teste de fumaça,
  configuração do ruff (regra proibindo `print` em `tabgen/core/`).
- Out: qualquer lógica de áudio/ML; dependências pesadas (torch, demucs, basic-pitch) — entram
  nas tarefas das etapas que as usam.

## Done criteria

- [ ] `pip install -e ".[dev]"` termina com exit 0 em venv Python 3.11.
- [ ] `tabgen --version` imprime a versão (ex.: `tabgen 0.1.0`).
- [ ] `pytest -q` verde (≥1 teste).
- [ ] `ruff check .` sem erros.
- [ ] `grep -rE "import typer|import rich|print\(" tabgen/core/` não retorna nada (core puro).

## Notes

Código e comentários em inglês (en-US). Nome do pacote PyPI reservável: `tabgen` pode estar
ocupado — verificar e, se preciso, usar nome de distribuição alternativo mantendo o import `tabgen`.

## Execution Log
