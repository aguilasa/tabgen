# Profile — refinamento

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
- 2026-10-25 — Técnicas: bends/slides a partir dos pitch bends do Basic Pitch; hammer-on/pull-off por heurística de onsets fracos; palm mute fora (precisa de classificador) — plano, seção 5 (Fase 4).
- 2026-10-25 — Formato-alvo `.gp5` via PyGuitarPro; GPX/GP6+ fora — plano, seção 3 (Estágio 6).
- 2026-10-25 — Licença MIT; modelos non-commercial aceitos; Essentia (AGPL) evitada — plano, seção 4.
- 2026-10-25 — Idiomas: código e commits em en-US (conventional), documentação do Rite em pt-BR — definido pelo usuário na adoção do Rite.

## Sources of truth

<!-- Plan sections, specs, reference outputs. Items point here through `source_of_truth`. -->

- Plano do projeto: [/docs/planejamento/audio-para-tablatura.md](/docs/planejamento/audio-para-tablatura.md) — roadmap Fase 4 (seção 5), estágios 4–6 (seção 3), datasets de avaliação (seção 6), limitações (seção 7).

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

### Fase 4 — Refinamento

- `.venv/bin/tabgen export <amostra>.mp3 -o out.gp5` sai 0; `guitarpro.parse` reabre e notas com técnica detectada carregam o efeito correspondente.
- `--no-techniques` gera .gp5 sem efeitos; `--bass-tuning five-string` gera faixa de baixo com 5 cordas.
- `.venv/bin/python scripts/probe_e2e_export.py` e `scripts/probe_e2e_sample.py` saem 0.
- Relatório de avaliação reproduzível: o comando registrado em `scripts/eval/` regenera nota-F1 e tab-F1 do subset versionado.
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
