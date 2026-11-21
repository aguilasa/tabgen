---
id: FIX-STEM-001
---

# FIX-STEM-001 — Decodificar mix e stems como o Demucs antes da harmonia

Origin: [STEM-TASK-01](/docs/rite/cycles/entrada-stems/01-separacao-preparada-a-partir-de-stems-dados-no.md)

## Problem

Quando os stems dados cobrem todos os instrumentos, `prepared_separate` entrega o `input_path` cru à
harmonia, como stem `mix`. `sum_harmonic_stems` (`tabgen/core/analysis/harmony.py:66`) lê os stems com
soundfile e exige uma taxa de amostragem única. Com isso:
- mix em 48 kHz e stem em 44,1 kHz dão `HarmonyError`;
- mix em `.m4a` dá `LibsndfileError` cru, e não `PipelineError`.

Sem `--stem` essas duas entradas funcionam, porque o Demucs converte a entrada antes
(`demucs.py:77`). No caso parcial, um stem dado com taxa diferente da do Demucs (44,1 kHz) tem o
mesmo problema.

## Evidência

```text
$ D=$(mktemp -d) && .venv/bin/python - "$D" <<'PY'
import sys, numpy as np, soundfile
from pathlib import Path
from tabgen.core.pipeline import run_analysis
d = Path(sys.argv[1])
soundfile.write(str(d/"song.wav"), np.zeros((48000*2, 2), np.float32), 48000)
soundfile.write(str(d/"guitar.wav"), np.zeros((44100*2, 2), np.float32), 44100)
def boom(*a, **k): raise AssertionError("demucs called")
class B: tempo_bpm=120.0; beat_times=[]; downbeat_times=[]
try:
    run_analysis(d/"song.wav", user_stems={"guitar": d/"guitar.wav"}, separate_fn=boom,
                 beats_fn=lambda p, on_progress=None: B())
    print("OK")
except Exception as e:
    print(type(e).__name__, e)
PY
HarmonyError stem sample rates differ: mix has 48000 Hz, expected 44100 Hz
```

## Root cause

`prepared.py` repassa o mix e os stems dados como chegaram, sem converter com ffmpeg nem reamostrar para
uma taxa comum. Os testes usam só wav de 44,1 kHz.

## Fix

Em `tabgen/core/separation/prepared.py`, converter o mix e os stems dados para wav numa taxa única
(44,1 kHz estéreo, a do Demucs) antes de repassá-los. A conversão reaproveita a mesma rotina ffmpeg do
`demucs.py`, e os arquivos convertidos ficam em cache ao lado da entrada. Falhas da conversão viram
`PipelineError`. Teste novo em `tests/test_prepared_stems.py`: mix de 48 kHz com stem de 44,1 kHz.

## Arquivos

- tabgen/core/separation/prepared.py
- tests/test_prepared_stems.py

## Verificação

O script da Evidência imprime `OK`. Com entrada `.m4a`, imprime `OK` ou uma `PipelineError`, nunca
`LibsndfileError`. `.venv/bin/pytest -q tests/test_prepared_stems.py` passa.

## Execution Log
