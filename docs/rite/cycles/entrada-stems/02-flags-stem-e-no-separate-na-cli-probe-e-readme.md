---
id: STEM-TASK-02
---

# STEM-TASK-02 — Flags --stem e --no-separate na CLI, probe e README

## Goal

`tabgen export`, `transcribe` e `analyze` passam a aceitar `--stem INSTRUMENTO=ARQUIVO` (repetível) e
`--no-separate`. Um probe reproduzível mostra um export real a partir de um stem wav, sem Demucs, e o
README explica o uso com stems do Moises.

## Escopo

- In:
  - `tabgen/cli/main.py`:
    - `--stem` aceita `guitar=caminho` e `bass=caminho`. Formato inválido, instrumento desconhecido
      ou arquivo inexistente → mensagem "Invalid option" e exit 2.
    - `--no-separate`: o áudio de entrada vira o stem do único instrumento pedido. Com mais de um
      instrumento em `--instruments` → exit 2.
    - As flags são repassadas como `user_stems` ao core.
  - `scripts/probe_e2e_stems.py`:
    - Sintetiza um stem de guitarra determinístico (Karplus-Strong, 10 s) e roda
      `tabgen export ... --no-separate --instruments guitar`. Não usa `stems/guitar.wav`: esse arquivo
      não é versionado, e um número só vale se for reproduzível a partir do HEAD (regra do CLAUDE.md).
    - Imprime o tempo total e se o Demucs foi carregado, e confere o `.gp5` com `guitarpro.parse`.
    - Sai 0.
  - README: seção "Using stems you already have" com `--stem` e `--no-separate`.
- Out:
  - Worker NDJSON e desktop.

## Done criteria

- [x] `.venv/bin/pytest -q tests/test_cli_stems.py` passa, cobrindo:
  - `--stem guitar=x.wav` chega ao core como `user_stems`;
  - `--stem foo=x.wav` → exit 2;
  - `--no-separate --instruments guitar,bass` → exit 2;
  - stem inexistente → exit 2.
- [x] `.venv/bin/python scripts/probe_e2e_stems.py` sai 0. Ele imprime `demucs_loaded=False` e
      `gp5 ok`, e o tempo medido vai para o Execution Log.
- [x] `.venv/bin/tabgen export --help | grep -E -- "--stem|--no-separate"` lista as duas flags.
- [x] `grep -n "no-separate" README.md` acha a seção nova.

## Execution Log

- **Closed** — commit `89dd225` (2026-11-21): feat(cli): add --stem and --no-separate to export, transcribe and analyze
  - Files (`git show --name-status 89dd225`):
    - `M README.md`
    - `M docs/rite/cycles/entrada-stems/02-flags-stem-e-no-separate-na-cli-probe-e-readme.md`
    - `A scripts/probe_e2e_stems.py`
    - `M tabgen/cli/main.py`
    - `A tests/test_cli_stems.py`
- **Reviewed** (2026-11-21) at `f043edd`: FIX-STEM-003, FIX-STEM-004, FIX-STEM-005, FIX-STEM-006
