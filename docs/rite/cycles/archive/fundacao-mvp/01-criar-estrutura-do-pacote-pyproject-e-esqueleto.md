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

Decisão: nome de distribuição mantido como `tabgen` (sem publicação neste ciclo); se ocupado na
hora de publicar, só `[project].name` muda (ex.: `tabgen-cli`), o import continua `tabgen`.

Verificação (venv Python 3.11.15 em `.venv/`, git-ignorada):

- `.venv/bin/pip install -e ".[dev]"` → exit 0
- `.venv/bin/tabgen --version` → `tabgen 0.1.0`
- `.venv/bin/pytest -q` → `2 passed in 0.03s`
- `.venv/bin/ruff check .` → `All checks passed!`
- `grep -rE "import typer|import rich|print\(" tabgen/core/` → sem saída, exit 1 (core puro)

Guarda do ruff validada por controle: um `print` de teste em `tabgen/core/separation/__init__.py`
fez `ruff check` falhar com T201; removido, árvore limpa. `requires-python = ">=3.10,<3.12"`
(restrição do madmom). Entry point `tabgen = "tabgen.cli.main:app"`.

## Execution Log

- **Closed** — commit `f102f43` (2026-10-26): feat: scaffold tabgen package with typer CLI, pyproject, and smoke test
  - Files (`git show --name-status f102f43`):
    - `A pyproject.toml`
    - `A tabgen/__init__.py`
    - `A tabgen/cli/__init__.py`
    - `A tabgen/cli/main.py`
    - `A tabgen/core/__init__.py`
    - `A tabgen/core/analysis/__init__.py`
    - `A tabgen/core/export/__init__.py`
    - `A tabgen/core/fretting/__init__.py`
    - `A tabgen/core/separation/__init__.py`
    - `A tabgen/core/transcription/__init__.py`
    - `A tests/test_smoke.py`
  - **Outside declared files** (`pyproject.toml`, `tabgen/__init__.py`, `tabgen/core/__init__.py`, `tabgen/cli/main.py`, `tests/test_smoke.py`):
    - `tabgen/cli/__init__.py`
    - `tabgen/core/analysis/__init__.py`
    - `tabgen/core/export/__init__.py`
    - `tabgen/core/fretting/__init__.py`
    - `tabgen/core/separation/__init__.py`
    - `tabgen/core/transcription/__init__.py`
- **Reviewed** (2026-10-26) at `262c740`: no finding
