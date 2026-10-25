---
id: FMVP-TASK-05
---

# FMVP-TASK-05 — Implementar separação de fontes com Demucs e comando separate

## Goal

Existe o estágio 1 do pipeline (plano, Estágio 1): `tabgen/core/separation/` embrulha o Demucs
v4 — `htdemucs_ft` (vocais, bateria, baixo, outros) e `htdemucs_6s` (stem de guitarra) — e
produz um `SeparationResult` com stems em wav, usando o cache e emitindo progresso por
callback. `tabgen separate musica.mp3` grava os stems em `stems/` ao lado do áudio.

## Escopo

- In: conversão de entrada via ffmpeg (mp3/flac/wav → wav 44.1 kHz), wrapper Demucs (pacote
  `demucs` do fork adefossez, API Python, device cuda/cpu autodetectado), fusão das saídas dos
  dois modelos num `SeparationResult` (baixo/bateria/vocais/outros do `_ft`, guitarra do `_6s`),
  cache por estágio, subcomando `separate` com barra de progresso.
- Out: transcrição; qualquer análise musical; BS-RoFormer/MDX23 (upgrade futuro).

## Done criteria

- [ ] `tabgen separate <amostra>.mp3` sai 0 e grava `stems/{vocals,drums,bass,other,guitar}.wav`;
      cada wav abre com `soundfile` e dura ±0,5 s do original.
- [ ] Segunda execução do mesmo comando usa o cache: não re-roda o Demucs (log/flag indica
      `cache hit`) e termina em <5 s.
- [ ] Teste unitário com modelo mockado cobre fusão dos stems e o caminho do cache.
- [ ] `tabgen separate --device cpu` funciona (mais lento, sem CUDA).
- [ ] `pytest -q` e `ruff check .` verdes.

## Notes

Pesos baixam no primeiro uso (~3 GB) para o cache do torch — doctor (TASK-03) já checa espaço.
Amostra de teste: usar trecho curto (≤30 s) para o teste real ficar rápido; não commitar áudio
(já no .gitignore).

## Execution Log
