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

Verificação (venv `.venv/`, amostra sine 220 Hz 10 s em scratchpad, fora do repo):

- 1ª execução `tabgen separate sample.mp3` → exit 0, 27,3 s (CUDA); grava
  `stems/{vocals,drums,bass,other,guitar}.wav`; soundfile: original 10,031 s, stems 10,000 s
  @ 44100 Hz (±0,5 s ok).
- 2ª execução → `cache hit: stems reused, Demucs skipped.`, 0,202 s total (<5 s) — medido
  na thread principal.
- `--device cpu` → exit 0, 165 s user (CPU real) vs 13 s user em CUDA.
- `pytest -q tests/test_separation.py` → `4 passed` (fusão ft+6s, cache sem recompute,
  stem apagado invalida cache, progresso 0–100).
- `pytest -q` → `33 passed` · `ruff check .` → limpo · grep core puro → vazio, exit 1.

Desenho: demucs 4.1.0 + soundfile 0.14.0; `demucs.api.Separator`; htdemucs_ft
(vocals/drums/bass/other) + htdemucs_6s (só guitar; piano descartado) → um `SeparationResult`.
Cache estágio "separation", versão "htdemucs_ft+htdemucs_6s" (device fora da chave); entrada
com stems apagados vira miss. Segment 7 s (limite htdemucs 7,8 s) para caber em 6 GB VRAM —
sem OOM na RTX 3060. Progresso: _ft 0–80%, _6s 80–100%. Conversão de entrada via ffmpeg
(qualquer formato → wav estéreo 44,1 kHz). Injeção `separator_factory` para testes mockados.
Pesos via HF Hub no cache do torch (fora do repo); aviso stderr "unauthenticated requests"
vem da lib, inofensivo.

## Execution Log

- **Closed** — commit `9b243dc` (2026-10-26): feat(separation): add Demucs-based source separation and separate command
  - Files (`git show --name-status 9b243dc`):
    - `M pyproject.toml`
    - `M tabgen/cli/main.py`
    - `M tabgen/core/separation/__init__.py`
    - `A tabgen/core/separation/demucs.py`
    - `A tests/test_separation.py`
- **Reviewed** (2026-10-26) at `00a11af`: FIX-FMVP-004
