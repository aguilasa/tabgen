---
id: TAB-TASK-02
---

# TAB-TASK-02 — Quantizar notas na grade de beats

## Goal

Existe `tabgen/core/export/quantize.py` (ou módulo próprio em `core/`): projeta onset/offset de
cada `Note` na grade de beats/downbeats do `AnalysisResult`, com resolução de semicolcheia por
padrão e tercinas detectadas por ajuste, devolvendo posição (compasso, tempo, subdivisão) e
duração em subdivisões. É a etapa que define se a tab "parece certa" (plano, Estágio 6).

## Escopo

- In: grade de subdivisões entre beats consecutivos (andamento variável respeitado); compasso a
  partir dos downbeats; snap de onset e duração mínima de 1 subdivisão; detecção de tercina por
  erro de ajuste menor; notas antes do primeiro downbeat (anacruse) tratadas; testes com grades
  sintéticas.
- Out: fretting (TASK-03); fórmula de compasso variável (Fase 4).

## Done criteria

- [x] Teste: notas exatamente em semicolcheias a 120 BPM 4/4 (com jitter aleatório ±20 ms, seed
      fixa) voltam nas posições originais (compasso, tempo, subdivisão) em 100% dos casos.
- [x] Teste: três notas igualmente espaçadas num beat são quantizadas como tercina, não como
      semicolcheias.
- [x] Teste: grade com andamento variável (beats com intervalos crescentes) mantém cada nota no
      beat correto.
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado: afirmar fatos estáveis (posições), não contagens frágeis. Referência para
comparação: MuseScore CLI (plano, seção 6) — opcional.

Implementação: `tabgen/core/export/quantize.py`, entrada principal
`quantize_notes(notes, beat_times, downbeat_times, subdivisions_per_beat=4,
triplet_subdivisions=3, beats_per_measure=None, detect_triplets=True)` →
`list[QuantizedNote]` (dataclass pura, sem string/fret — o fretting do TASK-03 atribui à parte).

Convenções documentadas no docstring do módulo:
- Posição contínua em unidades de beat calculada sobre os `beat_times` reais (tempo variável
  respeitado); fora da grade, extrapola o primeiro/último intervalo entre beats.
- Tercina decidida por beat: grade de 3 vence quando o erro total de snap dos onsets do beat é
  estritamente menor que o da grade de 4; `subdivisions_in_beat` registra a grade vencedora.
- Anacruse: notas antes do primeiro downbeat caem no compasso 0 (beats contando para trás a
  partir do primeiro downbeat; ex.: pickup de 1 beat em 4/4 = compasso 0, beat 4).
- Onset arredondado para a linha do próximo beat "carrega" (beat seguinte, subdivisão 0).
- Duração = offset snapado − onset snapado na grade do próprio beat da nota, piso 1 subdivisão.
- `beats_per_measure` inferido da mediana do espaçamento (em beats) entre downbeats; fallback 4
  com downbeat único/ausente; fórmula de compasso constante (variável fica para a Fase 4).

Comandos decisivos (saídas escopadas a este item):
- `.venv/bin/pytest tests/test_quantize.py -q` → `8 passed` (cobre jitter ±20 ms com
  `random.Random(42)`, tercina, tempo variável, anacruse, extrapolação, carry e duração mínima).
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → sem saída (exit 1).
- `.venv/bin/ruff check .` → `All checks passed!`; `.venv/bin/pytest -q` → suíte verde.

## Execution Log

- **Closed** — commit `f84b965` (2026-10-27): feat(export): quantize note times onto the beat grid with triplet detection
  - Files (`git show --name-status f84b965`):
    - `M docs/rite/cycles/tablatura/02-quantizar-notas-na-grade-de-beats.md`
    - `A tabgen/core/export/quantize.py`
    - `A tests/test_quantize.py`
