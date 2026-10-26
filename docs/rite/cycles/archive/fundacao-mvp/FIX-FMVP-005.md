---
id: FIX-FMVP-005
---

# FIX-FMVP-005 — Registrar comando de geração da amostra por trás dos números de verificação

Origin: [FMVP-TASK-07](/docs/rite/cycles/archive/fundacao-mvp/07-exportar-midi-por-instrumento-e-comando.md)

## Problem

As Notes da FMVP-TASK-07 afirmam `guitar: 1 notes` e `859/858` mensagens de pitch-wheel para a
amostra de verificação, mas a especificação registrada ("sine 220 Hz 10 s" mp3) omite o comando
do encoder; regenerando pela spec (ffmpeg lavfi sine, `-q:a 2`) sai `guitar: 3 notes` (pitches
35 e 57) e 783 pitch-wheels na guitarra — o baixo reproduz exato (1 nota, MIDI 57, 858 wheels),
então a divergência depende do encode. A medição foi ad hoc: nenhum probe versionado a
reconstrói a partir do HEAD.

## Evidência

```text
$ ffmpeg -y -f lavfi -i "sine=frequency=220:duration=10" -q:a 2 sample.mp3   # scratch, fora do repo
$ /home/ingmar/development/tabgen/.venv/bin/tabgen transcribe sample.mp3
guitar: 3 notes -> sample.guitar.mid
bass: 1 notes -> sample.bass.mid
```

(Notes da task afirmam `guitar: 1 notes` e 859 pitch-wheels na guitarra; medido 3 notas / 783.)

## Root cause

Hipótese: a amostra original foi codificada com outros parâmetros de mp3 (bitrate/qualidade), e
as detecções espúrias de pitch grave do Basic Pitch variam com artefatos de encode; o comando
exato de geração não foi escrito nas Notes de verificação da task.

## Fix

Adicionar o comando exato de geração da amostra (invocação ffmpeg completa) às Notes de
verificação da task — via fluxo do Rite, nunca à mão — ou, melhor, versionar um probe de
integração marcado como lento (ex.: `tests/test_e2e_sample.py` atrás de marker, ou probe em
`scripts/`) que gera a amostra senoidal deterministicamente e afirma só fatos estáveis da
amostra (exit 0, mido reabre, ≥1 nota, pitch 57 presente), não contagens exatas de notas.

## Arquivos

- `docs/rite/cycles/fundacao-mvp/07-exportar-midi-por-instrumento-e-comando.md` (via Rite)
- opcionalmente `tests/` ou `scripts/` para o probe

## Verificação

Regenerar a amostra com o comando registrado e rodar `tabgen transcribe`; os números do resumo
devem bater com as Notes (hoje não batem para a guitarra), ou o novo probe passa onde hoje não
existe probe algum.

Medido após o fix (2026-10-26):

```text
$ .venv/bin/python scripts/probe_e2e_sample.py; echo "exit=$?"
PASS: transcribe exit 0; both .mid written and reopened by mido; bass has 1 note(s) with pitch 57 present (guitar: 2 note(s), count not asserted).
exit=0
```

(Guitarra mediu 2 notas nesta execução — 1/3/4 nas anteriores — confirmando que só os fatos
estáveis asseridos pelo probe são reprodutíveis.)

## Execution Log

- 2026-10-26 — Triagem (`rite reproduce FIX-FMVP-005`): REPRODUCED.

  ```text
  $ ffmpeg -y -f lavfi -i "sine=frequency=220:duration=10" -q:a 2 sample.mp3
  $ /home/ingmar/development/tabgen/.venv/bin/tabgen transcribe sample.mp3
  guitar: 4 notes -> sample.guitar.mid
  bass: 1 notes -> sample.bass.mid
  ```

  Notes da task afirmam `guitar: 1 notes`; Evidência original mediu 3; hoje 4. A contagem exata
  deriva entre execuções/encodes — confirma o sintoma (números não reprodutíveis, sem probe
  versionado) e a prescrição de afirmar só fatos estáveis.
- **Closed** — commit `c0ec1bc` (2026-10-26): chore(scripts): add e2e sample probe and record sample generation command
  - Files (`git show --name-status c0ec1bc`):
    - `M docs/rite/cycles/fundacao-mvp/07-exportar-midi-por-instrumento-e-comando.md`
    - `A scripts/probe_e2e_sample.py`
