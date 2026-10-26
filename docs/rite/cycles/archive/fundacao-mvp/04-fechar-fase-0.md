---
id: FMVP-TASK-04
---

# FMVP-TASK-04 — Fechar Fase 0

## Goal

A Fase 0 (fundação) está verificada de ponta a ponta: pacote instalável, contratos com cache,
`tabgen doctor` funcional, gates verdes e checks da fase executados.

## Escopo

- In: re-executar gates e os checks da Fase 0 do profile; corrigir pequenas pendências de
  integração entre as tarefas 01–03; atualizar README com instruções de instalação reais.
- Out: qualquer funcionalidade nova.

## Done criteria

- [ ] Em venv limpa: `pip install -e ".[dev]"` → `tabgen --version` → `tabgen doctor` exit 0.
- [ ] `pytest -q` e `ruff check .` verdes.
- [ ] `grep -rE "import typer|import rich|print\(" tabgen/core/` vazio.
- [ ] README descreve instalação e doctor (seções testáveis copiando/colando os comandos).

## Notes

Verificação Fase 0 ponta a ponta, venv limpa (Python 3.11.15 via mise, scratch temporária):

- `pip install -e ".[dev]"` → exit 0 (inclui torch 2.14.1)
- `tabgen --version` → `tabgen 0.1.0`
- `tabgen doctor` → exit 0; `✓ ffmpeg /usr/bin/ffmpeg` · `✓ python 3.11.15` ·
  `✓ torch+cuda 2.14.1+cu130, RTX 3060 Laptop GPU (5.7 GB VRAM)` · `✓ disk 907.4 GB free`
- `pytest -q` → `29 passed, 1 warning` (venv limpa e `.venv/` dev) · `ruff check .` → limpo
- `grep -rE "import typer|import rich|print\(" tabgen/core/` → vazio, exit 1

README reescrito (en-US): instalação copiável, nota do índice CUDA do torch (encaminhada da
FMVP-TASK-03), uso de `tabgen --version`/`doctor`/`doctor --json`, dev (pytest, ruff), licença
MIT com nota de modelos non-commercial. Sem pendências de integração entre 01–03. Observações
benignas: torch avisa "Failed to initialize NumPy" (numpy entra nos estágios de áudio); GPU
reporta 5.7 GB utilizáveis vs ≥6 GB nominais recomendados no README.

## Execution Log

- **Closed** — commit `796284b` (2026-10-26): docs: expand README with install, usage, dev, and license sections
  - Files (`git show --name-status 796284b`):
    - `M README.md`
- **Reviewed** (2026-10-26) at `49d1ebb`: no finding
