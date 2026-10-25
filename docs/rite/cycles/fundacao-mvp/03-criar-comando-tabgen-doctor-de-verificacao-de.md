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

## Execution Log
