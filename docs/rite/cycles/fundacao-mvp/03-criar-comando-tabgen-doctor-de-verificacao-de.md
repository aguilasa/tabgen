---
id: FMVP-TASK-03
---

# FMVP-TASK-03 — Criar comando tabgen doctor de verificação de ambiente

## Goal

Existe `tabgen doctor`, que verifica os requisitos do plano (seção 8) e reporta cada item:
ffmpeg no PATH, Python 3.10–3.11, PyTorch instalado e CUDA disponível (nome da GPU e VRAM),
espaço em disco para pesos de modelos (~4 GB). Sai com 0 quando tudo essencial passa, 1 quando falta algo.

## Escopo

- In: `tabgen/core/doctor.py` (checagens puras retornando estrutura de resultados),
  `tabgen/cli/` renderiza a lista com ✓/✗; flag `--json` imprime o resultado bruto; testes
  com checagens mockadas.
- Out: download de modelos; instalação automática de dependências.

## Done criteria

- [ ] `tabgen doctor` na máquina de dev sai com exit 0 e lista ffmpeg, versão do Python,
      torch+CUDA (nome da GPU) e espaço em disco.
- [ ] `tabgen doctor --json` imprime JSON parseável (`python -m json.tool` aceita).
- [ ] Teste simulando ffmpeg ausente → exit 1 e item marcado como falha.
- [ ] `pytest -q` e `ruff check .` verdes.

## Notes

torch entra como dependência aqui (necessária para checar CUDA) — instalar a variante CUDA
documentando o índice correto no README.

Verificação (venv `.venv/`, Python 3.11.15):

- `.venv/bin/tabgen doctor` → exit 0; lista: `✓ ffmpeg /usr/bin/ffmpeg` · `✓ python 3.11.15` ·
  `✓ torch+cuda PyTorch 2.14.1+cu130, NVIDIA GeForce RTX 3060 Laptop GPU (5.7 GB VRAM)` ·
  `✓ disk space 912.9 GB free`
- `.venv/bin/tabgen doctor --json | python -m json.tool` → JSON válido
- `pytest -q tests/test_doctor.py::test_cli_doctor_exits_1_when_ffmpeg_absent` → passa (mock
  `shutil.which`→None; exit 1)
- `.venv/bin/pytest -q` → `29 passed, 1 warning` · `.venv/bin/ruff check .` → `All checks passed!`

torch 2.14.1+cu130 (wheel PyPI padrão, já com CUDA no Linux). Aviso stderr no import do torch:
"Failed to initialize NumPy: No module named 'numpy'" — numpy ainda não é dependência; entra nos
estágios de áudio. Encaminhado: documentar no README o índice CUDA do torch
(`pip install torch --index-url https://download.pytorch.org/whl/cuXXX` quando precisar de build
específico) — dica deixada como comentário no `pyproject.toml`; README fica para a FMVP-TASK-04.

## Execution Log

- **Closed** — commit `48913ae` (2026-10-26): feat: add tabgen doctor environment check command
  - Files (`git show --name-status 48913ae`):
    - `M pyproject.toml`
    - `M tabgen/cli/main.py`
    - `A tabgen/core/doctor.py`
    - `A tests/test_doctor.py`
