# Profile — analise-musical

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
- 2026-10-25 — Estágios 2–3 (tom, acordes, beats/downbeats/BPM) com madmom; alternativas (Beat This!, Essentia, Chordino) só se o madmom falhar — plano, seção 3.
- 2026-10-25 — Licença MIT; modelos non-commercial (madmom CC BY-NC-SA) aceitos — plano, seção 4.
- 2026-10-25 — Idiomas: código e commits em en-US (conventional), documentação do Rite em pt-BR — definido pelo usuário na adoção do Rite.

## Sources of truth

<!-- Plan sections, specs, reference outputs. Items point here through `source_of_truth`. -->

- Plano do projeto: [/docs/planejamento/audio-para-tablatura.md](/docs/planejamento/audio-para-tablatura.md) — estágios 2–3 (seção 3), roadmap Fase 2 (seção 5), arquitetura (seção 2), licenças (seção 4).

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

### Fase 2 — Análise musical

- `.venv/bin/python -c "from madmom.features import downbeats, key, chords"` sai 0 no venv do projeto.
- `.venv/bin/tabgen analyze <amostra>.mp3` sai 0, imprime tom, BPM e sequência de acordes, e grava JSON que `AnalysisResult.from_json` recarrega.
- Segunda execução reusa o cache `.tabgen/` (`cache hit`, sem madmom nem Demucs; <5 s).
- Click track sintético de 120 BPM é medido em 120 ± 2 BPM pelo estágio de beats.
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
