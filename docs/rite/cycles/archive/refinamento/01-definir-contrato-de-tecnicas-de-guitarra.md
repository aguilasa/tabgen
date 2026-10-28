---
id: REF-TASK-01
---

# REF-TASK-01 — Definir contrato de técnicas de guitarra

## Goal

Os contratos carregam técnicas de guitarra: `Note` (`tabgen/core/models.py`) ganha os pitch
bends do Basic Pitch (hoje só em `TranscriptionResult.bends`, fora do contrato), e `TabNote` ganha
um campo de técnica tipado — bend (semitons alvo e curva simplificada), slide (para cima/baixo,
nota de destino), hammer-on, pull-off — serializável em JSON e com round-trip testado.

## Escopo

- In: campo `bends` opcional em `Note` (lista de bins 1/3 de semitom ou `None`) com transcrição
  passando a preenchê-lo; dataclass de técnica em `TabNote` (default: nenhuma); `from_dict`
  retrocompatível (JSON sem os campos novos carrega); versão de formato do contrato incrementada
  nas chaves de cache que o usam.
- Out: detecção (TASK-02/03); export (TASK-04); palm mute (decidido fora, precisa de classificador).

## Done criteria

- [x] `.venv/bin/pytest -q tests/test_models.py` verde, com round-trip de `TabScore` cujas notas têm
      bend, slide, hammer-on e pull-off, e de `NoteEvents` com bends.
- [x] Teste: JSON gerado antes da mudança (fixture versionada sem os campos novos) carrega com
      `from_json` e técnicas vazias.
- [x] Teste: a versão de cache de transcrição e de tablatura muda (entrada antiga vira miss).
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-TAB-001): a convenção de cada campo novo fica no docstring do contrato, não
em prosa de tarefa. Pitfall "Cache hit valida identidade": contrato muda ⇒ versão de cache muda.

Decisões de design:

- `Note.bends: list[int] | None = None` (bins de 1/3 de semitom relativos a `pitch_midi`, um por
  frame do modelo); `_to_result` preenche direto na nota. O payload de cache da transcrição passa a
  ser só `{"note_events": ...}` (bends viajam dentro de cada nota).
- `TranscriptionResult.bends` ficou como espelho de compatibilidade: no `__post_init__`, entradas
  dadas no construtor são copiadas para notas sem bends e o campo é sempre reconstruído a partir
  das notas. Assim `export_midi(..., bends=...)` (fora da lista de arquivos) mantém o contrato de
  chamada; `run_transcription` passa `[n.bends for n in notes]`.
- `Technique(kind, bend_semitones, bend_curve, slide_direction, target_fret)` com constantes
  `TECHNIQUE_BEND/SLIDE/HAMMER_ON/PULL_OFF`, `TECHNIQUE_KINDS`, `SLIDE_UP/DOWN`; validação no
  `__post_init__` (kind conhecido, bend > 0, slide com direção). `TabNote.technique: Technique |
  None = None`; `TabNote.from_dict` reconstrói o dataclass aninhado. Convenção (no docstring):
  a técnica fica na nota de ORIGEM (convenção Guitar Pro) — slide/hammer-on/pull-off ligam esta
  nota à próxima na mesma corda; `target_fret` = traste de destino; `bend_curve` = offsets em
  semitons amostrados uniformemente do ataque ao fim da nota (vazio = bend simples e sustentado).
- Versões: `TAB_FORMAT_VERSION` 1 → 2; novo `NOTE_CONTRACT_REVISION = 2` em `models.py`, usado em
  `transcription_version(instrument)` (novo, `basic_pitch.py`) e também em `tablature_version`.
- Fixture pré-mudança: `tests/fixtures/contracts_v1.json`, gerada pelo `to_json` do código anterior
  (antes de editar `models.py`), com um `TabScore` e um `NoteEvents`.

Rascunho de evidência (o main thread reexecuta):

- `.venv/bin/pytest -q tests/test_models.py` — verde (round-trip com as quatro técnicas, `NoteEvents`
  com bends, fixture v1, versões de cache).
- `.venv/bin/pytest -q` e `.venv/bin/ruff check .` — verdes.
- Controle: com `TAB_FORMAT_VERSION = 1` e sem o sufixo `+note-…` nas duas versões, os dois testes
  `-k cache_version` falham em `assert new_version != OLD_TRANSCRIPTION_VERSION` e
  `assert new_version != old_version`; restaurado, passam.

Verificação (2026-10-27, thread principal, árvore do commit):

- `.venv/bin/pytest -q tests/test_models.py` → `31 passed in 0.12s`
- `.venv/bin/pytest -q tests/test_models.py -k cache_version` → `2 passed, 29 deselected`
  (versões novas: `basic-pitch-icassp2022-onnx-guitar+note-2` e `tab-2+rev-1+...+note-2+params-...`)
- `.venv/bin/pytest -q` → `137 passed, 11 warnings`; `.venv/bin/ruff check .` → `All checks passed!`
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1)
- Fora da lista declarada e justificado: `tests/fixtures/contracts_v1.json` (fixture exigida pelo
  critério 2) e as notas encaminhadas nas REF-TASK-02/03/04.

## Execution Log

- **Closed** — commit `cb6063d` (2026-10-27): feat(core): add guitar technique contract and move pitch bends onto Note
  - Files (`git show --name-status cb6063d`):
    - `M docs/rite/cycles/refinamento/01-definir-contrato-de-tecnicas-de-guitarra.md`
    - `M docs/rite/cycles/refinamento/02-detectar-bends-e-slides-a-partir-dos-pitch-bends.md`
    - `M docs/rite/cycles/refinamento/03-detectar-hammer-on-e-pull-off-por-onsets-fracos.md`
    - `M docs/rite/cycles/refinamento/04-exportar-tecnicas-em-gp5-musicxml-e-ascii-e.md`
    - `M tabgen/core/models.py`
    - `M tabgen/core/pipeline.py`
    - `M tabgen/core/transcription/basic_pitch.py`
    - `A tests/fixtures/contracts_v1.json`
    - `M tests/test_models.py`
  - **Files amended** — added to `files`:
    - `docs/rite/cycles/refinamento/02-detectar-bends-e-slides-a-partir-dos-pitch-bends.md`
    - `docs/rite/cycles/refinamento/03-detectar-hammer-on-e-pull-off-por-onsets-fracos.md`
    - `docs/rite/cycles/refinamento/04-exportar-tecnicas-em-gp5-musicxml-e-ascii-e.md`
    - `tests/fixtures/contracts_v1.json`
- **Reviewed** (2026-10-27) at `864b6bd`: no finding
