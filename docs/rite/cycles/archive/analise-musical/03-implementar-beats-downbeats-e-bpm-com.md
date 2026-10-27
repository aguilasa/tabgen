---
id: ANA-TASK-03
---

# ANA-TASK-03 — Implementar beats, downbeats e BPM com DBNDownBeatTracker

## Goal

Existe `tabgen/core/analysis/beats.py`: dado um wav, roda o `DBNDownBeatTrackingProcessor`
do madmom e devolve tempos de beats, downbeats e BPM (mediana dos intervalos entre beats),
preenchendo os campos de ritmo do `AnalysisResult`. Core puro: progresso por callback, sem print.

## Escopo

- In: wrapper sobre `RNNDownBeatProcessor` + `DBNDownBeatTrackingProcessor` (beats_per_bar
  [3, 4]); cálculo do BPM; injeção de processador para testes mockados; teste com click track
  sintético gerado no próprio teste.
- Out: detecção de mudanças de fórmula de compasso / Beat This! (Fase 4); quantização (Fase 3).

## Done criteria

- [ ] Teste com click track sintético de 120 BPM em 4/4 (gerado em `tmp_path`, ≥10 s) mede BPM
      em 120 ± 2 e intervalo mediano
      entre downbeats = 4 beats.
- [ ] Teste unitário com processador mockado cobre o mapeamento saída-madmom → campos do
      `AnalysisResult` e os eventos de progresso 0 → 100.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/analysis/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

O teste do click real é lento (modelos RNN do madmom): se passar de ~10 s, marcar com marker
`slow` e registrar como rodar. Pitfall herdado: números nas Notes vêm com o comando versionado
que os gera.

Verificação (venv `.venv/`, madmom 0.17.dev0 real):

- `pytest -q tests/test_analysis_beats.py` → `6 passed in 1.63s`. Click track 12 s, 120 BPM 4/4
  (downbeats acentuados 1500 Hz): BPM medido = 120.0 (tolerância 118–122), 24 beats /
  6 downbeats, diffs de downbeat [1.98, 2.0, 2.0, 2.0, 2.0] — mediana 2.0 s = 4 beats.
  Teste real roda em ~1,5 s → sem marker `slow`.
- Teste mockado: array (N,2) → beat_times/downbeat_times/BPM 120.0; progresso
  "analysis:beats" 0→100 monotônico. Extras: saída vazia, 1 beat → BPM 0.0, arquivo ausente,
  shape inválido.
- `grep -rnE "import typer|import rich|print\(" tabgen/core/analysis/` → vazio, exit 1.
- `pytest -q` → `65 passed` (árvore só desta task) · `ruff check .` → limpo.

Desenho: `analyze_beats(audio_path, on_progress, processor)` → `BeatAnalysis(tempo_bpm,
beat_times, downbeat_times)` parcial, caller mescla no `AnalysisResult`; processador injetável
(default RNNDownBeatProcessor + DBNDownBeatTrackingProcessor(beats_per_bar=[3,4], fps=100),
imports do madmom lazy); BPM = 60/mediana dos intervalos entre beats.

## Execution Log

- **Closed** — commit `d63564f` (2026-10-26): feat(analysis): add beat/downbeat/BPM stage on madmom DBNDownBeatTracker
  - Files (`git show --name-status d63564f`):
    - `M tabgen/core/analysis/__init__.py`
    - `A tabgen/core/analysis/beats.py`
    - `A tests/test_analysis_beats.py`
- **Reviewed** (2026-10-26) at `efc5089`: no finding
