---
id: STEM-TASK-03
---

# STEM-TASK-03 — Fechar Fase 6

## Goal

Fecha a Fase 6 (entrada de stems): os gates passam no HEAD e as checagens da fase, no profile, foram
conferidas.

## Escopo

- In:
  - Rodar os gates e as checagens da Fase 6 do profile `entrada-stems`.
  - Registrar os números no Execution Log.
- Out:
  - Código novo. O que falhar vira fix.

## Done criteria

- [x] `make test` e `make lint` saem 0 no HEAD.
- [x] `.venv/bin/python scripts/probe_e2e_stems.py` sai 0 com `demucs_loaded=False`.
- [x] Export real de um stem do Moises (`~/Documents/diversos/musica/you-and-i/you-and-i-lead-gb-major-139bpm-443hz.wav`,
      copiado para o scratchpad) com `--no-separate --instruments guitar`:
  - sai 0;
  - o `.gp5` reabre com `guitarpro.parse`;
  - o tempo de separação no log de progresso é ≈0.
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` vazio.

## Notes

Medido em 2026-11-21 no HEAD depois do FIX-STEM-006 (RTX 3060):
- `make test` → `284 passed`; `make lint` → `All checks passed!`.
- `.venv/bin/python scripts/probe_e2e_stems.py`:
  - `demucs_loaded=False`
  - `gp5 ok: 20 guitar notes`
  - `cold export: 10.7 s`
  - `warm export (--stem, cache hit): 0.2 s`
  - `probe ok`
- Stem real do Moises:
  - Arquivo copiado para o scratchpad:
    `cp ~/Documents/diversos/musica/you-and-i/you-and-i-lead-gb-major-139bpm-443hz.wav $W/lead.wav`.
  - Comando: `tabgen export lead.wav --no-separate --instruments guitar --tuning half-step-down -o lead.gp5`.
  - Resultado:
    - exit 0, em `103.75 s` (`/usr/bin/time`);
    - barra `separation` em `100% 0:00:00`;
    - nenhuma pasta `stems/` criada;
    - o mix entrou em `.tabgen/user-stems/` (o wav do Moises não está no formato do Demucs).
  - A saída dá `Key: F# major` e `guitar: 516 notes`.
  - Cache: a análise e a tablatura usam a tag `+stems-ab079fa433+`. O nome mais longo tem 246 bytes (`ls .tabgen | awk "{print length}"`), abaixo do limite de 255.
  - Conferências do `.gp5`:
    - `guitarpro.parse` reabre o arquivo; o `gp_info.py` da skill `tablatura-guitar-pro` dá
      `problemas: 0`, 51 compassos e afinação eb;
    - `timeout 25 flatpak run ar.com.tuxguitar.TuxGuitar lead.gp5` sai com exit 124 (abriu e ficou
      aberto até o timeout).
  - Comparação: em 29/10 o mesmo wav, passado pelo Demucs, levou ao `.gp5` de 509 notas que está em
    `~/Documents/diversos/musica/you-and-i/`.
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` sai vazio (exit 1).

## Execution Log

- **Closed** — commit `d9de920` (2026-11-21): docs: correct cache name length in phase 6 closing evidence
  - Files (`git show --name-status d9de920`):
    - `M docs/rite/cycles/entrada-stems/03-fechar-fase-6.md`
