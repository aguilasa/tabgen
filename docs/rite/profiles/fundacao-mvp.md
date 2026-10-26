# Profile — fundacao-mvp

<!--
The cycle profile is read by every /rite command in this cycle. Keep it short
(rite.toml [profile].max_kb); dated pitfall histories go to the pitfalls file,
which commands search instead of reading whole.
-->

## Confirmed decisions

<!-- Decisions the user confirmed. One line each, with the date and where it was decided. -->

- 2026-10-25 — Linguagem Python 3.10–3.11 (madmom limita versão) — plano, seção 1.
- 2026-10-25 — Arquitetura em camadas: `core/` biblioteca pura (sem print/HTTP/GUI; progresso via callbacks), `cli/` camada fina; web/desktop futuras reutilizam o core — plano, seção 2.
- 2026-10-25 — Contratos entre estágios são dataclasses serializáveis em JSON, com cache em disco (`.tabgen/`) — plano, seção 2.
- 2026-10-25 — Stack por estágio: Demucs v4 (separação), madmom (tom/acordes/beats), Basic Pitch (áudio→notas), programação dinâmica própria (corda/casa), music21 + PyGuitarPro (exportação) — plano, seção 3.
- 2026-10-25 — Formato-alvo de saída: `.gp5` (PyGuitarPro); MusicXML, MIDI e tab ASCII secundários — plano, seções 3 e 4 (tabela de compatibilidade).
- 2026-10-25 — Licença do projeto: MIT; modelos non-commercial (madmom CC BY-NC, pesos Demucs) aceitos — uso livre/pessoal — plano, seção 4.
- 2026-10-25 — Idiomas: código e commits em en-US (conventional), documentação do Rite em pt-BR — definido pelo usuário na adoção do Rite.

## Sources of truth

<!-- Plan sections, specs, reference outputs. Items point here through `source_of_truth`. -->

- Plano do projeto: [/docs/planejamento/audio-para-tablatura.md](/docs/planejamento/audio-para-tablatura.md) — pipeline (seção 3), arquitetura (seção 2), roadmap em fases (seção 5), licenças (seção 4).

## Generated artifacts

<!-- Output -> generator -> check command. Never edit the output. -->

## Gates

<!-- Commands that must pass before any item of this cycle closes (in addition to rite.toml [gates].global). -->

- `.venv/bin/pytest -q` (a partir da FMVP-TASK-01, que cria a suíte)
- `.venv/bin/ruff check .`

## Hot files

<!-- Files many items touch; batches serialize on them. -->

- `tabgen/cli/main.py` — tarefas 01, 03, 05 e 07 adicionam subcomandos.
- `pyproject.toml` — tarefas 01, 03, 05 e 06 adicionam dependências.
- `tabgen/core/pipeline.py` — tarefas 02 e 07.

## Serialized resources

<!-- Cycle-specific resources that cannot be used by two workers at once (rite.toml [resources] has repo-wide ones). -->

## Pull-ahead precedents

<!-- When the user allowed work from a later task to be done early, and why. -->

## Phase-specific checks

<!-- One entry per phase used by tasks ("### Phase 1 — ..."). The reviewer runs these; a phase without an entry is a finding. -->

### Fase 0 — Fundação

- `pip install -e ".[dev]"` em venv limpa termina com exit 0.
- `tabgen --version` imprime a versão.
- `pytest -q` e `ruff check .` verdes.
- `grep -rE "import typer|import rich|print\(" tabgen/core/` não retorna nada (core sem I/O de interface).
- `tabgen doctor` sai 0 e lista ffmpeg, Python, torch+CUDA e espaço em disco.

### Fase 1 — Separar + MIDI

- `tabgen separate <amostra>.mp3` gera `stems/{vocals,drums,bass,other,guitar}.wav` válidos.
- `tabgen transcribe <amostra>.mp3` gera `.mid` por instrumento que o `mido` reabre sem erro.
- Segunda execução reusa o cache `.tabgen/` (sem re-rodar Demucs; termina em segundos).
- Teste de callbacks confirma eventos de progresso por estágio.
