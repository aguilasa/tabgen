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
    - Pega 20 s de um stem real (o padrão é o `stems/guitar.wav` da raiz, se existir; senão, um sinal
      Karplus-Strong sintetizado) e roda `tabgen export ... --no-separate --instruments guitar`.
    - Imprime o tempo total e se o Demucs foi carregado, e confere o `.gp5` com `guitarpro.parse`.
    - Sai 0.
  - README: seção "Using stems you already have" com `--stem` e `--no-separate`.
- Out:
  - Worker NDJSON e desktop.

## Done criteria

- [ ] `.venv/bin/pytest -q tests/test_cli_stems.py` passa, cobrindo:
  - `--stem guitar=x.wav` chega ao core como `user_stems`;
  - `--stem foo=x.wav` → exit 2;
  - `--no-separate --instruments guitar,bass` → exit 2;
  - stem inexistente → exit 2.
- [ ] `.venv/bin/python scripts/probe_e2e_stems.py` sai 0. Ele imprime `demucs_loaded=False` e
      `gp5 ok`, e o tempo medido vai para o Execution Log.
- [ ] `.venv/bin/tabgen export --help | grep -E -- "--stem|--no-separate"` lista as duas flags.
- [ ] `grep -n "no-separate" README.md` acha a seção nova.

## Execution Log
