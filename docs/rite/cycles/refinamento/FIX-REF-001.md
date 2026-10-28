---
id: FIX-REF-001
---

# FIX-REF-001 — Update stale bends comment in export/midi.py

Origin: [REF-TASK-04](/docs/rite/cycles/refinamento/04-exportar-tecnicas-em-gp5-musicxml-e-ascii-e.md)

## Problem

`tabgen/core/export/midi.py:37-38` ainda diz que os pitch bends por nota vêm de
`TranscriptionResult.bends`; desde a REF-TASK-01 a fonte canônica é `Note.bends`
(`TranscriptionResult.bends` é só shim de compatibilidade drenado para as notas). As Notes da
REF-TASK-04 mandavam corrigir aqui; o Execution Log registra que a edição foi recusada pelo
sistema de permissões e deixada para o usuário — o arquivo segue intocado.

## Evidência

```text
$ grep -n "TranscriptionResult" tabgen/core/export/midi.py
38:# tabgen.core.transcription.basic_pitch.TranscriptionResult.bends).

$ grep -n "bends" tabgen/core/transcription/basic_pitch.py | sed -n '2,4p'
81:    """Output of :func:`transcribe`: the note events (bends live on notes).
83:    The pitch-bend data now lives on each :attr:`Note.bends
```

## Root cause

Edição em `tabgen/core/export/midi.py` negada pelo sistema de permissões durante a execução da
REF-TASK-04 (registrado no Execution Log da task); o comentário ficou para trás da mudança de
contrato da REF-TASK-01.

## Fix

Apontar o comentário de `tabgen/core/export/midi.py:37-38` para `Note.bends`
(`tabgen.core.models.Note`). Só comentário; sem mudança de comportamento. Estado do Rite só via
CLI (`sh "$RITE_HOME/bin/rite"`).

## Arquivos

- tabgen/core/export/midi.py

## Verificação

```text
! grep -q "TranscriptionResult.bends" tabgen/core/export/midi.py
```

Falha agora; passa após o fix. Depois: `.venv/bin/ruff check .` verde e
`sh "$RITE_HOME/bin/rite" check --quick --json` com 0 erros.

## Execution Log

- 2026-10-28 — Triagem inline (`rite reproduce --all --cycle refinamento`): REPRODUCED.
  `grep -n "TranscriptionResult" tabgen/core/export/midi.py` → linha 37 (comentário stale,
  deslocado 1 linha desde a Evidência); `basic_pitch.py` confirma fonte canônica `Note.bends`
  (linhas 81-84). Sintoma presente no HEAD.
- 2026-10-28 — Fix aplicado. Antes: `grep -q "TranscriptionResult.bends" tabgen/core/export/midi.py`
  saía com 0 (controle `! grep -q …` falhava). Comentário das linhas 36-37 reescrito para apontar
  a fonte canônica `Note.bends` (`tabgen.core.models.Note`); só comentário, sem mudança de
  comportamento. Depois: `! grep -q "TranscriptionResult.bends" tabgen/core/export/midi.py` passa
  (exit 0) e `grep -n "Note.bends"` → linha 37. Gates: `.venv/bin/ruff check .` → "All checks
  passed!"; `.venv/bin/pytest -q` → 213 passed, 11 warnings. Sweep de `TranscriptionResult.bends`
  no repositório: hits restantes só em docs históricos do Rite (fundacao-mvp/06, refinamento/01 e
  04), que relatam o estado da época — nada a corrigir.
- 2026-10-28 — Verificação final na árvore do commit:
  `! grep -q "TranscriptionResult.bends" tabgen/core/export/midi.py` passa;
  `.venv/bin/ruff check .` → All checks passed!; `.venv/bin/pytest -q` → 213 passed;
  `rite gates --id FIX-REF-001` → passed.
