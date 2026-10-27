---
id: FIX-TAB-005
---

# FIX-TAB-005 — Version a deterministic e2e probe for tabgen export

Origin: [TAB-TASK-07](/docs/rite/cycles/tablatura/07-orquestrar-tablatura-no-pipeline-com-cache-e.md)

## Problem

Todos os números e2e da seção Verificação da TAB-TASK-07 (guitarra 2167 notas / gp5 2225, baixo
854/887, 147 compassos, tom F# major, ascii 83319 bytes, elapsed 0.58 s/0.35 s) citam comandos
sobre "You and I.flac", arquivo que existiu só num scratchpad de sessão descartado — os comandos
citados não rodam e os números não podem ser recontados a partir do HEAD. O precedente do
projeto para exatamente este problema (FIX-FMVP-005) versionou um probe determinístico para o
e2e de transcribe; não existe equivalente para export.

## Evidência

```text
$ git ls-files scripts
scripts/probe_e2e_sample.py

$ grep -c "export" scripts/probe_e2e_sample.py
0

$ git ls-files | grep -iE '\.flac|\.mp3'
(vazio — o input citado `.venv/bin/tabgen export "You and I.flac" -o out.gp5` não tem referente executável no HEAD)
```

Revisão remediu o e2e ad hoc com a receita do probe existente
(`ffmpeg -y -f lavfi -i "sine=frequency=220:duration=10" -q:a 2 sample.mp3`): export gp5 exit 0,
guitarpro.parse reabre com guitarra 6 notas / baixo 4, musicxml reabre no music21, ascii 981
bytes, 2º run "cache hit: tablature reused, Demucs, Basic Pitch, madmom and fretting skipped."
em 0.37 s — o pipeline funciona; falta o probe versionado.

## Root cause

Hipótese (não provada): o e2e foi verificado contra a música privada do usuário no scratchpad
por realismo musical, e a tarefa fechou sem portar essa verificação para um probe determinístico
versionado, como o FIX-FMVP-005 fez para transcribe.

## Fix

Adicionar `scripts/probe_e2e_export.py` (ou estender `scripts/probe_e2e_sample.py`): regenerar a
amostra determinística (receita ffmpeg sine já no probe), rodar `tabgen export` para
gp5/musicxml/txt, afirmar reabribilidade (guitarpro.parse com ambas as faixas ≥1 nota,
music21.converter.parse, ASCII não vazio) e o cache hit na 2ª execução (<5 s) — afirmando apenas
fatos estáveis entre execuções; contagens exatas de notas ficam fora, como o probe existente já
faz. Os números históricos no doc da 07 permanecem como estão (doc é estado gerenciado pelo
Rite); o probe torna a re-verificação futura possível. Estado só via CLI
(`sh "$RITE_HOME/bin/rite"`).

## Arquivos

- scripts/probe_e2e_export.py (novo, ou scripts/probe_e2e_sample.py)
- tests opcionais

## Verificação

```text
.venv/bin/python scripts/probe_e2e_export.py
```

Falha agora (`No such file or directory`); deve sair 0 após o fix. Depois:
`.venv/bin/pytest -q` verde e `sh "$RITE_HOME/bin/rite" check --quick --json` com 0 erros.

## Execution Log

- 2026-10-27 — Triagem inline (`rite reproduce --all --cycle tablatura`): REPRODUCED.
  `git ls-files scripts` → só `probe_e2e_sample.py`; `grep -c "export"` nele → 0; nenhum
  .flac/.mp3 versionado. Probe de export inexistente no HEAD.
- 2026-10-27 — Fix aplicado: adicionado `scripts/probe_e2e_export.py` (standalone, não coletado
  pelo pytest; espelha a estrutura e os helpers de `probe_e2e_sample.py`, inclusive
  `sys.stdout.write` por causa do ruff T20 em scripts/). O probe regenera a amostra determinística
  (ffmpeg sine 220 Hz/10 s em tempdir), roda `tabgen export` para gp5/musicxml/txt e reroda o gp5
  afirmando só fatos estáveis: exit 0, gp5 reaberto por guitarpro.parse com ≥1 nota em guitarra e
  baixo, musicxml reaberto por music21.converter.parse, ASCII não vazio e "cache hit" no stdout da
  2ª execução (tempo medido é informativo, não assert). Nada é escrito na árvore do repositório.
  Controle antes do fix: `.venv/bin/python scripts/probe_e2e_export.py` → exit 2
  (`No such file or directory`). Depois do fix: exit 0 — cauda medida:
  `PASS: export exit 0 for gp5/musicxml/ascii; gp5 reopened by guitarpro with notes in both
  tracks (bass: 4, guitar: 9; counts not asserted); musicxml reopened by music21; ASCII tab
  non-empty (981 bytes); cached rerun mentioned 'cache hit' in 0.26 s.`
  Gates: `.venv/bin/pytest -q` → 127 passed (probe não coletado); `.venv/bin/ruff check .` →
  All checks passed!
- 2026-10-27 — Verificação final na árvore do commit (demais itens em stash):
  `.venv/bin/python scripts/probe_e2e_export.py` → exit 0, cauda: `PASS: export exit 0 for
  gp5/musicxml/ascii; ... (bass: 4, guitar: 5; counts not asserted); ... ASCII tab non-empty
  (687 bytes); cached rerun mentioned 'cache hit' in 0.25 s.` (contagens/bytes variam entre
  execuções — por isso não são assertados); `.venv/bin/pytest -q` → 127 passed;
  `.venv/bin/ruff check .` → All checks passed!; `rite gates --id FIX-TAB-005` → passed.
- **Closed** — commit `d660056` (2026-10-27): test(e2e): version deterministic probe for tabgen export
  - Files (`git show --name-status d660056`):
    - `M docs/rite/cycles/tablatura/FIX-TAB-005.md`
    - `A scripts/probe_e2e_export.py`
