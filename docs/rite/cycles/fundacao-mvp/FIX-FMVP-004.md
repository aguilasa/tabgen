---
id: FIX-FMVP-004
---

# FIX-FMVP-004 — Validação de cache hit devolve stems de outra música após colisão

Origin: [FMVP-TASK-05](/docs/rite/cycles/fundacao-mvp/05-implementar-separacao-de-fontes-com-demucs-e.md)

## Problem

Os stems sempre caem no diretório compartilhado `stems/` ao lado do input, e
`_cached_result_is_valid` só checa que os arquivos de stem existem
(`tabgen/core/separation/demucs.py:202-207`). Separar a música B na mesma pasta sobrescreve os
stems da música A; re-rodar a música A então reporta "cache hit" e devolve o áudio da música B
como stems de A — resultado silenciosamente errado alimentando todos os estágios seguintes,
alcançável pela CLI entregue (`tabgen separate a.mp3; tabgen separate b.mp3;
tabgen separate a.mp3`).

## Evidência

```text
$ cd /home/ingmar/development/tabgen && .venv/bin/python - <<'EOF'
import tempfile
from pathlib import Path
import numpy as np, soundfile
from tabgen.core.separation import demucs as d
SR = 44100
def make_factory(fill):
    class Fake:
        samplerate = SR
        def separate_audio_file(self, file):
            import torch
            stems = {n: torch.full((2, SR), fill) for n in
                     ("vocals", "drums", "bass", "other", "guitar", "piano")}
            return torch.zeros(2, SR), stems
    return lambda model, device, segment, cb: Fake()
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    soundfile.write(tmp / "song_a.wav", np.full((SR, 2), 0.1, dtype=np.float32), SR)
    soundfile.write(tmp / "song_b.wav", np.full((SR, 2), 0.9, dtype=np.float32), SR)
    d.separate(tmp / "song_a.wav", device="cpu", separator_factory=make_factory(0.1))
    d.separate(tmp / "song_b.wav", device="cpu", separator_factory=make_factory(0.9))
    ra2, hit = d.separate(tmp / "song_a.wav", device="cpu", separator_factory=make_factory(0.1))
    guitar, _ = soundfile.read(ra2.stems["guitar"])
    print(f"cache_hit={hit}, guitar mean={guitar.mean():.2f} (A wrote 0.1, B wrote 0.9)")
    assert hit and abs(guitar.mean() - 0.9) < 0.05, "no collision"
    print("CONFIRMED: cache hit for song A returns song B's stems")
EOF
cache_hit=True, guitar mean=0.90 (A wrote 0.1, B wrote 0.9)
CONFIRMED: cache hit for song A returns song B's stems
```

## Root cause

Hipótese (sustentada pelo código): a chave de cache é por hash do input, mas os artefatos de
stem apontados vivem num caminho compartilhado por todos os inputs do diretório, e a validação
de hit checa apenas `Path(path).is_file()`, não que os arquivos ainda pertencem a este input
(nenhum tamanho/hash/identidade guardado no payload, nenhum subdiretório de stems por input).

## Fix

Em `tabgen/core/separation/demucs.py`: ou gravar os stems em diretório por input (ex.:
`stems/<nome do input>/` ou incluindo o hash do input), ou registrar a identidade de cada stem
(tamanho + mtime ou hash de conteúdo) no payload cacheado e comparar em
`_cached_result_is_valid`; adicionar teste de regressão em `tests/test_separation.py` cobrindo
dois inputs no mesmo diretório. Nota de severidade: todos os done criteria como escritos ainda
passam (fluxo de arquivo único está correto); o defeito vive um passo fora do caminho feliz
especificado, mas a própria spec manda o `stems/` compartilhado, então o fix pertence à
validação do cache.

## Arquivos

- `tabgen/core/separation/demucs.py`
- `tests/test_separation.py`

## Verificação

Mesmo heredoc da Evidência, com a asserção final invertida —
`assert abs(guitar.mean() - 0.1) < 0.05, "song A got song B's stems"` (e aceitando `hit` False).
Hoje falha (guitar mean 0.90); deve passar depois do fix.

## Execution Log
