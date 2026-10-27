---
id: FIX-TAB-002
---

# FIX-TAB-002 — Align key spellings with madmom minor labels and compare match by pitch class

Origin: [TAB-TASK-04](/docs/rite/cycles/tablatura/04-cruzar-tom-detectado-com-histograma-de-notas.md)

## Problem

Os KEY_LABELS do madmom grafam quatro tons menores com sustenidos (C#, D#, F#, G# minor), mas a
tabela canônica `_TONIC_NAMES` de `tabgen/core/analysis/key_check.py` usa bemóis (exceto F#)
para ambos os modos, enquanto o comentário do módulo (linhas 55-56) afirma que a tabela casa com
KEY_LABELS. Consequências observáveis no HEAD: (a) quando o madmom diz "C# minor" e as notas
estão exatamente em C# menor, `reason` volta "relative" em vez do documentado "match"
(`check_key` linha 246 compara strings, não pitch classes); (b) `relative_key("F# major")`
retorna "Eb minor" onde o madmom grafaria "D# minor", então tons menores com sustenido nunca
casam por string com o estágio de análise. `key`, `agreement` e `switched` finais permanecem
corretos (decisão é por pitch class) — só o `reason` sai errado e a claim do comentário é falsa.

## Evidência

```text
$ sed -n '14,19p' .venv/lib/python3.11/site-packages/madmom/features/key.py
... 'C# minor', 'D minor', 'D# minor', ... 'F# minor', 'G minor', 'G# minor']

$ .venv/bin/python - <<'EOF'
from tabgen.core.analysis.key_check import check_key, relative_key
from tabgen.core.models import Note, NoteEvents
pitches = [61, 63, 64, 66, 68, 69, 71]  # C# natural minor
notes, start = [], 0.0
for p in pitches:
    d = 2.0 if p == 61 else 0.5
    notes.append(Note(pitch_midi=p, start_s=start, end_s=start + d))
    start += d
r = check_key("C# minor", 0.9, [NoteEvents(notes=notes, instrument="guitar")])
print(r.histogram_key, r.reason, r.agreement, r.key)
print(relative_key("F# major"))
EOF
Db minor relative True C# minor
Eb minor
```

## Root cause

Hipótese: a tabela de grafia canônica foi derivada só dos rótulos de tons maiores do madmom; os
menores do madmom usam sustenidos, e a distinção match/relative compara strings renderizadas em
vez de `(pitch_class, mode)` parseados.

## Fix

Em `tabgen/core/analysis/key_check.py`: distinguir "match" vs "relative" por
`(pitch_class, mode)` parseados em vez de igualdade de string; e usar grafias canônicas por modo
casando com os KEY_LABELS do madmom (ou corrigir o comentário das linhas 55-56 — menores do
madmom usam sustenidos). Adicionar teste de regressão em `tests/test_key_check.py`.
Estado do Rite só via CLI (`sh "$RITE_HOME/bin/rite"`).

## Arquivos

- tabgen/core/analysis/key_check.py
- tests/test_key_check.py

## Verificação

```text
.venv/bin/python - <<'EOF'
from tabgen.core.analysis.key_check import check_key
from tabgen.core.models import Note, NoteEvents
pitches = [61, 63, 64, 66, 68, 69, 71]
notes, start = [], 0.0
for p in pitches:
    d = 2.0 if p == 61 else 0.5
    notes.append(Note(pitch_midi=p, start_s=start, end_s=start + d))
    start += d
r = check_key("C# minor", 0.9, [NoteEvents(notes=notes, instrument="guitar")])
assert r.reason == "match", r.reason
EOF
```

Falha agora (`AssertionError: relative`); deve passar após o fix. Depois:
`.venv/bin/pytest tests/test_key_check.py -q` verde.

## Execution Log

- 2026-10-27 — Triagem inline (`rite reproduce --all --cycle tablatura`): REPRODUCED. Script da
  Evidência imprime `Db minor relative True C# minor` e `relative_key("F# major")` → `Eb minor`,
  igual ao registrado: `reason` sai "relative" onde deveria ser "match" e a grafia não casa com
  os KEY_LABELS do madmom (menores com sustenido).
- 2026-10-27 — Fix aplicado. Reproduzi antes: script da Evidência imprimiu
  `Db minor relative True C# minor` / `Eb minor` e o script de Verificação falhou com
  `AssertionError: relative`. Mudanças em `tabgen/core/analysis/key_check.py`: tabela única
  `_TONIC_NAMES` substituída por `_TONIC_NAMES_BY_MODE` com grafias por modo casando exatamente
  com os KEY_LABELS do madmom (maiores com bemóis exceto F#; menores com sustenidos exceto Bb),
  comentário corrigido, `key_name` passou a escolher a tabela pelo modo, e a distinção
  match/relative em `check_key` agora compara `parse_key(...)` (pitch class + modo) em vez de
  strings renderizadas. Regressão em `tests/test_key_check.py`:
  `test_sharp_minor_key_matches_by_pitch_class` (C# menor → `reason == "match"`,
  `histogram_key == "C# minor"`) e `test_relative_key_mapping` atualizado
  (`relative_key("F# major") == "D# minor"`, `relative_key("C# minor") == "E major"`).
  Medido após o fix: Evidência imprime `C# minor match True C# minor` e `D# minor`;
  Verificação passa; `.venv/bin/pytest tests/test_key_check.py -q` → 8 passed;
  `.venv/bin/pytest -q` → 106 passed; `.venv/bin/ruff check .` → All checks passed.
  API pública (`check_key`, `relative_key`, campos de `KeyCheckResult`) inalterada; decisão
  final (`key`/`agreement`/`switched`) preservada.
- 2026-10-27 — Verificação final na árvore do commit: script da Verificação passa
  (`C# minor match True C# minor` | `relative_key("F# major")` → `D# minor`);
  `.venv/bin/pytest -q` → 106 passed; `.venv/bin/ruff check .` → All checks passed!;
  `rite gates --id FIX-TAB-002` → passed (0 gates configurados no profile).
