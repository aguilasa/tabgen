---
id: FMVP-TASK-06
---

# FMVP-TASK-06 — Implementar transcrição áudio-notas com Basic Pitch

## Goal

Existe o estágio 4 do pipeline (plano, Estágio 4): `tabgen/core/transcription/` roda o
Basic Pitch sobre um stem wav e produz `NoteEvents` (onset, offset, pitch MIDI, confiança,
pitch bends) serializável e cacheado. Para o stem de baixo, aplica verificação de oitava
(limitar faixa à tessitura do baixo).

## Escopo

- In: wrapper do pacote `basic-pitch` (função `predict`), conversão da saída para `NoteEvents`,
  parâmetros por instrumento (faixa de frequência para baixo vs guitarra), preservação dos
  pitch bends no contrato (base para bends/slides na Fase 4), cache, testes com fixture de
  áudio sintético (senoides geradas em teste — pitch conhecido).
- Out: MIDI em disco (TASK-07); quantização; corda/casa.

## Done criteria

- [ ] Teste com wav sintético (ex.: A4 440 Hz, 1 s) retorna `NoteEvents` contendo nota pitch 69
      com onset <0,2 s de erro.
- [ ] Teste do perfil de baixo: nota sintética E1 (41 Hz) detectada sem salto de oitava
      (pitch 28, não 40).
- [ ] Resultado cacheado: segunda chamada não re-roda o modelo (contador/mock).
- [ ] `pytest -q` e `ruff check .` verdes.

## Notes

Basic Pitch é Apache 2.0 e leve (CPU ok). Dependência `basic-pitch` fixada em versão testada.
Atenção ao conflito potencial de versões de tensorflow/onnx com torch — preferir o backend
ONNX/CoreML se disponível para evitar TF completo.

## Execution Log
