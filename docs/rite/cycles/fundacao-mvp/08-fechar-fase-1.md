---
id: FMVP-TASK-08
---

# FMVP-TASK-08 — Fechar Fase 1

## Goal

A Fase 1 está verificada com música real: pipeline separa + transcreve uma gravação comercial
de teste de ponta a ponta na GPU, cache funciona entre execuções, gates e checks da fase
verdes, README atualizado com o uso real do MVP.

## Escopo

- In: rodada e2e com música real (escolhida pelo usuário), medição de tempos por estágio
  (separação, transcrição) registrada no Execution Log, revisão dos checks da Fase 1 do
  profile, atualização do README (uso, exemplos, tempos esperados).
- Out: melhorias de qualidade de transcrição (Fase 4); novos recursos.

## Done criteria

- [ ] `tabgen transcribe <música real>.mp3` completa sem erro na GPU; tempos por estágio
      anotados no Execution Log.
- [ ] `.mid` resultante abre no TuxGuitar (verificação manual confirmada pelo usuário ou
      screenshot anexado).
- [ ] Todos os checks da Fase 1 do profile passam.
- [ ] `pytest -q` e `ruff check .` verdes em venv limpa.

## Notes

Parte automatizável verificada (amostra sintética 10 s em scratchpad):

- Venv limpa (Python 3.11.15): `pip install -e ".[dev]"` → exit 0; passo do README
  `pip install --no-deps basic-pitch==0.4.0` → exit 0; `pytest -q` → `51 passed`;
  `ruff check .` → limpo; transcrição real na venv limpa (cache frio) → 2,2 s, mido reabre.
- Checks Fase 1: `tabgen separate` → 5 stems válidos (soundfile, 44,1 kHz, 10 s);
  `tabgen transcribe` FRIO na GPU → 9,48 s total (separação ~5 s, transcrição guitar ~1 s,
  resto <1 s); quente → 0,288 s com `cache hit`; mido reabre os dois `.mid`
  (guitar 2 notas, bass 1 nota); callbacks → `6 passed`.
- Integração (encaminhada da TASK-07): `"mido"` adicionado ao dev extras do `pyproject.toml`.
- README: passo do basic-pitch (conflito TF/numpy<2 explicado), uso de separate/transcribe,
  tabela de tempos indicativos (pendente validação com música real).
- Descoberta útil: cache de transcrição fica em `stems/.tabgen/` (chaveado pelo stem);
  o de separação em `.tabgen/` ao lado do input — README cobre ambos.

Pendente (humano): rodar `tabgen transcribe` numa música comercial escolhida pelo usuário,
anotar tempos por estágio no Execution Log, e abrir os `.mid` no TuxGuitar confirmando.

E2e com música real — "You and I.flac" (4 min 08 s, indicada pelo usuário; cópia em scratchpad
para não poluir a pasta de música) — `tabgen transcribe`, GPU RTX 3060 Laptop:

- Frio: 61,3 s total (`/usr/bin/time`): separação 47 s, transcrição guitar 6 s, bass 4 s;
  pico de RAM 3,9 GB. Saída: guitar 2203 notas, bass 857 notas.
- Quente: 1,5 s, `cache hit` em separação e transcrição.
- `mido.MidiFile` reabre ambos: guitar 2203 note_on / 242,2 s; bass 857 note_on / 246,1 s.

`.mid` enviados ao usuário para a verificação manual no TuxGuitar (último critério pendente).

## Execution Log

- **blocked** (2026-10-26): Trabalho coerente commitado em 1d4bdd3 (README, mido dev dep, venv limpa verde) e e2e com música real medido (61,3 s frio / 1,5 s quente, tempos no Notes). Falta só a verificação manual: usuário abrir You and I.{guitar,bass}.mid no TuxGuitar e confirmar.
