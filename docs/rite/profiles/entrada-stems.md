# Profile — entrada-stems

<!--
The cycle profile is read by every /rite command in this cycle. Keep it short
(rite.toml [profile].max_kb); dated pitfall histories go to the pitfalls file,
which commands search instead of reading whole.
-->

## Confirmed decisions

<!-- Decisions the user confirmed. One line each, with the date and where it was decided. -->

- 2026-11-21 — Aceitar stem pronto por flag no tabgen (não contornar fora do repo) — decidido pelo usuário ao planejar a skill global de tablatura.
- 2026-11-21 — `--stem INSTRUMENTO=ARQUIVO` repetível e `--no-separate` em export/transcribe/analyze; Demucs não roda quando todo instrumento pedido tem stem — plano, seção "Decisões" 1–3.
- 2026-11-21 — Sem `--stem`, versões de cache inalteradas; worker/desktop fora do escopo — plano, "Decisões" 5–6.

## Sources of truth

<!-- Plan sections, specs, reference outputs. Items point here through `source_of_truth`. -->

- Plano do ciclo: [/docs/planejamento/entrada-stems.md](/docs/planejamento/entrada-stems.md).

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

### Fase 6 — Entrada de stems

- `tabgen export <stem>.wav --no-separate --instruments guitar -o x.gp5` sai 0 sem carregar o Demucs (o probe `scripts/probe_e2e_stems.py` imprime `demucs_loaded=False`).
- `--stem guitar=<arquivo>` com mistura como entrada: os beats vêm da mistura e a faixa de guitarra vem do stem dado.
- Sem `--stem`, os caches existentes continuam válidos: as versões de `analysis` e `tablature` são iguais às do HEAD anterior ao ciclo.
- `make test` e `make lint` saem 0; `grep -rnE "import typer|import rich|print\(" tabgen/core/` vazio.

