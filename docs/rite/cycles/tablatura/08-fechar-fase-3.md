---
id: TAB-TASK-08
---

# TAB-TASK-08 — Fechar Fase 3

## Goal

A Fase 3 está verificada com música real: `tabgen export` gera .gp5 de uma gravação escolhida
pelo usuário, o arquivo abre no TuxGuitar (e/ou Guitar Pro) com faixas guitarra e baixo, tempos
medidos, checks e gates da fase verdes, README atualizado com uso e tempos do `export`.

## Escopo

- In: rodada e2e com música real; tempos frio/quente com o comando de medição; verificação
  manual no TuxGuitar pelo usuário; checks da Fase 3; README (uso, exemplo de ASCII, tempos,
  limitações da seção 7); venv limpa.
- Out: melhorias de qualidade (Fase 4).

## Done criteria

- [x] `.venv/bin/tabgen export <música real>.mp3 -o <música>.gp5` sai 0 na GPU; tempos frio e quente
      anotados com o comando de medição.
- [x] Usuário confirma que o .gp5 abre no TuxGuitar com faixas guitarra e baixo (registrado nas
      Notes).
- [x] Todos os checks da Fase 3 do profile passam.
- [x] Venv limpa: instalação documentada sai 0 e `.venv/bin/pytest -q` verde.
- [x] README tem seção do `export` com tempos medidos e as limitações (rascunho editável).
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-FMVP-006): números medidos no e2e vão para o README neste mesmo item.

Encaminhado pela TASK-07 (2026-10-27): opções do `export` para o README —
`-o FILE` (formato pelo sufixo `.gp5`/`.musicxml`/`.xml`/`.txt`), `--format gp5|musicxml|ascii`,
`--instruments guitar,bass`, `--tuning`/`--bass-tuning` (preset ou notas low-to-high, ex.
`D2,A2,D3,G3,B3,E4`), `--capo N` (só guitarra), `--device`. Medida parcial com caches
upstream quentes (`You and I.flac`): estágio tablatura frio 0.58 s, cache hit 0.35 s — o tempo
frio completo (separação + análise + transcrição + tablatura) ainda precisa ser medido aqui.

Verificação (2026-10-27, RTX 3060 Laptop, `torch.cuda.is_available()` → `True`):

- Música real: `You and I.flac` (4:08) — FLAC em vez de MP3; o decoder (ffmpeg) é o mesmo.
  Diretório novo no scratchpad, sem `.tabgen/` nem `stems/` (frio de verdade).
- Frio: `/usr/bin/time -f "elapsed=%es" .venv/bin/tabgen export "You and I.flac" -o "You and I.gp5"`
  → exit 0, `guitar: 2204 notes ... 29 unplayable`, `bass: 860 notes ... 4 unplayable`,
  `elapsed=192.75s`.
- Quente: mesmo comando → `cache hit: tablature reused, Demucs, Basic Pitch, madmom and fretting
  skipped.`, `elapsed=0.35s`.
- Checks da Fase 3: `guitarpro.parse` → `track guitar strings 6 notes 2271 measures 147`,
  `track bass strings 4 notes 901 measures 147`, `measures not summing to time signature: 0`;
  `-o out.musicxml` → exit 0, `music21.converter.parse` → `parts 2 measures 147`; `-o out.txt` →
  exit 0, `ascii bytes 83319`; `grep -rnE "import typer|import rich|print\(" tabgen/core/` →
  vazio (exit 1). `.venv/bin/python scripts/probe_e2e_export.py` → `PASS: ... cached rerun
  mentioned 'cache hit' in 0.29 s.`
- Usuário (2026-10-27): abriu `out/fase3/You and I.gp5` no TuxGuitar/Guitar Pro — "Abre, 2 faixas
  ok" (guitarra 6 cordas e baixo 4 cordas). Saídas copiadas para `out/fase3/` (não versionado;
  `out/` entrou no `.gitignore`).
- Venv limpa: Python 3.11.15 (mise) `-m venv`, `pip install -e ".[dev]"` → exit 0,
  `pip install --no-deps basic-pitch==0.4.0` → exit 0, `pytest -q` → `127 passed`.
- Gates: `.venv/bin/pytest -q` → `127 passed`; `.venv/bin/ruff check .` → `All checks passed!`.
- README: seção "Generate tablature (Guitar Pro, MusicXML, ASCII)" com uso, opções, exemplo de
  ASCII, limitações (plano, seção 7) e linhas `export` frio ~193 s / quente 0.35 s na tabela.

## Execution Log

- **Closed** — commit `64f438b` (2026-10-27): docs(readme): document tabgen export with measured runtimes and limitations
  - Files (`git show --name-status 64f438b`):
    - `M .gitignore`
    - `M README.md`
    - `M docs/rite/cycles/tablatura/08-fechar-fase-3.md`
  - **Outside declared files** (`README.md`):
    - `.gitignore`
