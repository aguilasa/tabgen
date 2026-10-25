---
id: FMVP-TASK-07
---

# FMVP-TASK-07 — Exportar MIDI por instrumento e comando transcribe

## Goal

Existe o MVP fim-a-fim da Fase 1 (plano, Fase 1): `tabgen transcribe musica.mp3` separa
(reusando o estágio 1), transcreve cada stem alvo (guitarra, baixo) e grava um `.mid` por
instrumento — abrível no TuxGuitar — mais um resumo no terminal (nº de notas por instrumento).

## Escopo

- In: `tabgen/core/export/midi.py` (NoteEvents → MIDI via mido/pretty_midi, com pitch bends),
  orquestração em `tabgen/core/pipeline.py` (separate → transcribe → export, com cache e
  callbacks), subcomando `transcribe` com `--instruments guitar,bass` e `--output-dir`.
- Out: .gp5/MusicXML (Fase 3); tom/acordes/compassos (Fase 2) — MIDI sai sem quantização,
  timestamps absolutos.

## Done criteria

- [ ] `tabgen transcribe <amostra>.mp3` sai 0 e grava `<amostra>.guitar.mid` e
      `<amostra>.bass.mid`.
- [ ] Cada `.mid` reabre com `mido` sem erro e contém ≥1 nota (teste automatizado na amostra).
- [ ] Com cache de separação quente, `transcribe` não re-roda o Demucs.
- [ ] Callbacks de progresso disparam para cada estágio (teste captura sequência de eventos).
- [ ] `pytest -q` e `ruff check .` verdes.

## Notes

Este é o entregável que já tem valor para o usuário final: ouvir no TuxGuitar o que foi
detectado. Divulgável como pré-release 0.1.

## Execution Log
