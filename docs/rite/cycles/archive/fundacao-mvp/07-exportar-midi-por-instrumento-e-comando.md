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

Verificação (venv `.venv/`, amostra sine 220 Hz 10 s em scratchpad, caches quentes):

- `tabgen transcribe sample.mp3` → exit 0; grava `sample.guitar.mid` e `sample.bass.mid`;
  resumo: `guitar: 1 notes` · `bass: 1 notes` (MIDI 57 = A3 = 220 Hz — pitch correto).
- `mido.MidiFile` reabre ambos sem erro; ≥1 nota em cada; bends presentes como pitch-wheel
  (859/858 mensagens).
- Cache quente: `cache hit: stems reused, Demucs skipped.` + `(cache hit)` por instrumento,
  0,237 s total — medido na thread principal.
- Teste de progresso: ordem separation → transcription:guitar → export:guitar →
  transcription:bass → export:bass, cada estágio chegando a 100.0.
- `pytest -q` → `51 passed` · `ruff check .` → limpo · grep core puro → vazio, exit 1.

Notas: export usa pretty_midi (mido só nos testes de releitura; mido 1.3.3 já estava na venv
como dependência do pretty_midi); bends do Basic Pitch (bins de 1/3 de semitom por frame)
viram pitch-wheel assumindo range ±2 semitons, com reset no fim da nota; `run_transcription`
injeta separate/transcribe/export para testes; `TranscriptionSummary`/`InstrumentSummary`
vivem em `pipeline.py` (models.py fora do escopo).

Encaminhamento: adicionar `"mido"` explícito em `[project.optional-dependencies].dev`
(testes importam direto; hoje é transitiva) — TASK-08.

Adendo (FIX-FMVP-005): a amostra da verificação acima foi gerada com
`ffmpeg -y -f lavfi -i "sine=frequency=220:duration=10" -q:a 2 sample.mp3`. As contagens
exatas de notas variam com artefatos do encode mp3 (guitar mediu 1/3/4 em execuções
distintas); estáveis são: exit 0, os dois `.mid` gravados e reabríveis com `mido`, e o
baixo com ≥1 nota incluindo pitch 57 (A3 = 220 Hz). A medição agora é reconstruível via
`scripts/probe_e2e_sample.py` (`.venv/bin/python scripts/probe_e2e_sample.py`), que
assere só esses fatos estáveis.

## Execution Log

- **Closed** — commit `db85cb3` (2026-10-26): feat(export): add per-instrument MIDI export, pipeline orchestration and transcribe command
  - Files (`git show --name-status db85cb3`):
    - `M tabgen/cli/main.py`
    - `A tabgen/core/export/midi.py`
    - `M tabgen/core/pipeline.py`
    - `A tests/test_midi_export.py`
    - `A tests/test_pipeline.py`
- **Reviewed** (2026-10-26) at `5dcd1e4`: FIX-FMVP-005
