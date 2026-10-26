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

## Execution Log
