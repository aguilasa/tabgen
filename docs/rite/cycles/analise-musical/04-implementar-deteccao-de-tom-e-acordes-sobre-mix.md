---
id: ANA-TASK-04
---

# ANA-TASK-04 — Implementar detecção de tom e acordes sobre mix sem bateria

## Goal

Existe `tabgen/core/analysis/harmony.py`: soma os stems harmônicos (mix sem bateria — todos os
stems do `SeparationResult` exceto `drums`) e roda sobre ela o reconhecimento de tom
(`CNNKeyRecognitionProcessor`) e de acordes (`CNNChordFeatureProcessor` +
`CRFChordRecognitionProcessor`), devolvendo tom e sequência de acordes com timestamps no
contrato da TASK-02.

## Escopo

- In: mixagem dos stems não-bateria em wav temporário/array; tom; acordes maior/menor por
  segmento com início/fim; fusão de segmentos consecutivos de mesmo rótulo; injeção de
  processadores para testes; teste com acordes sintéticos.
- Out: cruzamento do tom com o histograma de notas transcritas (decidido: Fase 3); acordes além
  de maior/menor; rodar a separação (vem pronta da TASK-05).

## Done criteria

- [ ] Teste com áudio sintético (tríades senoidais A menor → C maior → G maior, ~2 s cada,
      gerado em `tmp_path`) reconhece a sequência `A:min, C:maj, G:maj` (rótulos madmom) na ordem,
      e tom compatível (A minor ou C major).
- [ ] Teste unitário com stems falsos confirma que `drums` fica fora da soma e que segmentos
      vizinhos iguais são fundidos.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/analysis/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado: afirmar fatos estáveis do áudio sintético (ordem dos acordes), não contagem
exata de segmentos ou timestamps finos.

Verificação (venv `.venv/`, madmom 0.17.dev0 real, CPU ~4 s):

- `pytest -q tests/test_analysis_harmony.py` → `5 passed in 4.55s`. Saída real do madmom na
  progressão sintética Am–C–F–G–C (2 s cada, 4 harmônicos): acordes
  [(0.0,2.1,'A:min'), (2.1,4.0,'C:maj'), (4.0,6.0,'F:maj'), (6.0,8.0,'G:maj'),
  (8.0,10.0,'C:maj')] — contém A:min, C:maj, G:maj em ordem; tom "C major" (conf. 0.776).
- Mockado: stem `drums` fora da soma (processador injetado vê guitar+other = 0.3, nunca 0.5);
  fusão de segmentos consecutivos iguais [(0–1 A:min)+(1–2 A:min)+(2–3 C:maj)] →
  [(0,2,A:min),(2,3,C:maj)].
- `grep -rnE "import typer|import rich|print\(" tabgen/core/analysis/` → vazio, exit 1.
- `pytest -q` → `70 passed` · `ruff check .` → limpo.

Resultado negativo que virou iteração de fixture: Am(2s)–C(2s)–G(2s) puro dá rótulos de acorde
perfeitos mas tom "G major" (Am/C/G são todos diatônicos de G: ii–IV–I); a cadência vi–I–IV–V–I
(Am–C–F–G–C) resolve para "C major" sem relaxar asserções.

Desenho: `analyze_harmony(stems, …, key_processor, chord_feature_processor, chord_decoder) →
HarmonyResult(key, key_confidence, chords)`; soma mono dos stems não-bateria com zero-pad e
rescale se pico >0.99, mix em wav temporário passado aos dois pipelines; KEY_LABELS do madmom já
são "<tônica> <modo>", usados verbatim; progresso "analysis:harmony" 0/20/60/100.

Encaminhado à ANA-TASK-05: entry point e eventos acima.

## Execution Log

- **Closed** — commit `c9eaff4` (2026-10-26): feat(analysis): detect key and chords over drum-free mix with madmom
  - Files (`git show --name-status c9eaff4`):
    - `A tabgen/core/analysis/harmony.py`
    - `A tests/test_analysis_harmony.py`
- **Reviewed** (2026-10-26) at `dc18f9a`: no finding
