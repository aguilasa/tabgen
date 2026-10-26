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

## Execution Log
