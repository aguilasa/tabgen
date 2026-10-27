# Profile — tablatura

<!--
The cycle profile is read by every /rite command in this cycle. Keep it short
(rite.toml [profile].max_kb); dated pitfall histories go to the pitfalls file,
which commands search instead of reading whole.
-->

## Confirmed decisions

<!-- Decisions the user confirmed. One line each, with the date and where it was decided. -->

- 2026-10-25 — Linguagem Python 3.10–3.11 (madmom limita versão) — plano, seção 1.
- 2026-10-25 — Arquitetura em camadas: `core/` biblioteca pura (sem print/HTTP/GUI; progresso via callbacks), `cli/` camada fina — plano, seção 2.
- 2026-10-25 — Contratos entre estágios são dataclasses serializáveis em JSON, com cache em disco (`.tabgen/`) — plano, seção 2.
- 2026-10-25 — Estágio 5 v1: atribuição corda/casa por programação dinâmica sobre heurísticas, sem ML; afinação e nº de cordas configuráveis; acordes do estágio 2 como prior — plano, seção 3 (Estágio 5).
- 2026-10-25 — Estágio 6: quantização na grade de beats (semicolcheia padrão), music21 para partitura/MusicXML, PyGuitarPro para .gp5 — plano, seção 3 (Estágio 6).
- 2026-10-25 — Formato-alvo `.gp5`; MusicXML, MIDI e tab ASCII secundários — plano, seção 3 (compatibilidade de formatos).
- 2026-10-25 — Licença MIT; modelos non-commercial (madmom, pesos Demucs) aceitos — plano, seção 4.
- 2026-10-25 — Idiomas: código e commits em en-US (conventional), documentação do Rite em pt-BR — definido pelo usuário na adoção do Rite.
- 2026-10-26 — Cruzamento do tom com o histograma de notas transcritas fica na Fase 3 — decidido pelo usuário no planejamento do ciclo analise-musical.

## Sources of truth

<!-- Plan sections, specs, reference outputs. Items point here through `source_of_truth`. -->

- Plano do projeto: [/docs/planejamento/audio-para-tablatura.md](/docs/planejamento/audio-para-tablatura.md) — estágios 5–6 (seção 3), roadmap Fase 3 (seção 5), arquitetura (seção 2), limitações (seção 7).

## Generated artifacts

<!-- Output -> generator -> check command. Never edit the output. -->

## Gates

<!-- Commands that must pass before any item of this cycle closes (in addition to rite.toml [gates].global). -->

## Hot files

<!-- Files many items touch; batches serialize on them. -->

## Serialized resources

<!-- Cycle-specific resources that cannot be used by two workers at once (rite.toml [resources] has repo-wide ones). -->

## Pull-ahead precedents

<!-- When the user allowed work from a later task to be done early, and why. -->

## Phase-specific checks

<!-- One entry per phase used by tasks ("### Phase 1 — ..."). The reviewer runs these; a phase without an entry is a finding. -->

### Fase 3 — Tablatura

- `.venv/bin/tabgen export <amostra>.mp3 -o out.gp5` sai 0 e `guitarpro.parse` reabre o arquivo com faixas guitarra e baixo.
- `-o out.musicxml` reabre no `music21.converter.parse`; `-o out.txt` gera tab ASCII não vazia.
- Segunda execução reusa o cache `.tabgen/` (`cache hit`, sem Demucs, Basic Pitch, madmom nem DP; <5 s).
- Compassos do .gp5 relido somam exatamente a fórmula de compasso (sem compasso incompleto).
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
