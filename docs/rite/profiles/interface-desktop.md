# Profile — interface-desktop

<!--
The cycle profile is read by every /rite command in this cycle. Keep it short
(rite.toml [profile].max_kb); dated pitfall histories go to the pitfalls file,
which commands search instead of reading whole.
-->

## Confirmed decisions

<!-- Decisions the user confirmed. One line each, with the date and where it was decided. -->

- 2026-10-28 — Stack da desktop: Tauri 2 + sidecar Python (worker consome o core); aprovada pelo usuário junto com o protótipo — spec, seção 2.
- 2026-10-28 — Protótipo aprovado como referência visual: https://claude.ai/artifact/7AvMdpWdyaD56TYHeikJou — spec, cabeçalho.
- 2026-10-28 — Escopo v1 espelha a CLI (pipeline completo); player por stem, tab renderizada, biblioteca e edição ficam para v2 — spec, seção 1.
- 2026-10-28 — Protocolo UI↔worker: NDJSON em stdin/stdout, um job por processo; cancelar = encerrar o worker (core sem cancelamento) — spec, seções 2–3.
- 2026-10-28 — v1 usa a instalação Python existente (venv); empacotar Python fica para depois — spec, seção 2.
- 2026-10-25 — Arquitetura em camadas: `core/` puro; `desktop/` e `tabgen/worker/` são camadas finas — plano geral, seção 2.
- 2026-10-25 — Idiomas: código e commits em en-US (conventional), documentação do Rite em pt-BR — adoção do Rite.

## Sources of truth

<!-- Plan sections, specs, reference outputs. Items point here through `source_of_truth`. -->

- Spec da desktop: [/docs/planejamento/interface-desktop.md](/docs/planejamento/interface-desktop.md) — escopo (1), arquitetura (2), protocolo (3), telas (4), empacotamento (5), roadmap (6).
- Plano geral: [/docs/planejamento/audio-para-tablatura.md](/docs/planejamento/audio-para-tablatura.md) — arquitetura (seção 2), Fase 5 (seção 5).
- Protótipo navegável aprovado: https://claude.ai/artifact/7AvMdpWdyaD56TYHeikJou

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

### Fase 5 — Interface desktop

- `printf '{"cmd":"doctor","args":{}}\n' | .venv/bin/python -m tabgen.worker` emite só NDJSON e termina com `{"type":"result",…}`, exit 0.
- `cd desktop && npm run build` e o typecheck do frontend saem 0.
- No app (`tauri dev` ou AppImage): pipeline da amostra roda com barras por estágio real e a segunda execução mostra cache em <5 s.
- Export .gp5 feito pelo app reabre com `guitarpro.parse` (faixas guitarra e baixo).
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
