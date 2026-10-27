---
id: REF-TASK-03
---

# REF-TASK-03 — Detectar hammer-on e pull-off por onsets fracos

## Goal

Existe heurística de legato: uma nota cujo ataque é fraco (velocity/amplitude bem abaixo da
nota anterior), que começa logo ao fim da anterior e fica na mesma corda vira hammer-on (pitch
sobe) ou pull-off (pitch desce), preenchendo a técnica da `TabNote` (plano, Fase 4).

## Escopo

- In: critérios nomeados (razão de amplitude, gap máximo, mesma corda, intervalo ≤ 5 casas);
  aplicada depois do fretting; testes sintéticos.
- Out: tapping, trinados como técnica própria; classificador de ML.

## Done criteria

- [ ] Teste: casa 5 forte seguida de casa 7 com amplitude 30% e gap 0 na mesma corda vira
      hammer-on; 7 → 5 nas mesmas condições vira pull-off.
- [ ] Teste: mesma sequência com segunda nota forte, com gap > limiar ou em outra corda não vira
      legato.
- [ ] Teste: primeira nota de um compasso após pausa nunca é marcada como legato.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Heurística sem ground truth local; a qualidade real é medida pelo harness (TASK-06) se o dataset
tiver anotação de técnica (EGDB/Guitar-TECHS) — registrar se não tiver.

### Áudio de teste (YouTube)

Pode baixar áudio de músicas conhecidas no YouTube com `yt-dlp` (instalado, 2026.08.19)
para conferir a detecção em gravação real.

Candidatas com hammer-on e pull-off claros:

- AC/DC — "Back in Black" (riff principal: hammer-ons e pull-offs na corda solta).
- Jimi Hendrix — "Little Wing" (intro: hammer-ons em formas de acorde).
- Led Zeppelin — "Stairway to Heaven" (solo: sequências de pull-off).

O áudio fica fora do repositório (`out/` ou scratchpad, ambos ignorados; nunca versionar), é
usado só para conferência e não vira número de done criterion: pela regra do `CLAUDE.md`, arquivo
baixado não é evidência reproduzível — os critérios continuam nos testes e probes sintéticos.
Baixar só o trecho necessário (`--download-sections`) quando possível. Se o `yt-dlp` falhar ou o
vídeo não existir, trocar por outra música da lista e registrar nas Notes.

```sh
yt-dlp -x --audio-format mp3 -o 'out/audio/%(title)s.%(ext)s' "ytsearch1:<artista> <música>"
yt-dlp -x --audio-format mp3 --download-sections '*<mm:ss>-<mm:ss>' -o 'out/audio/%(title)s.%(ext)s' "ytsearch1:<artista> <música>"
```

## Execution Log
