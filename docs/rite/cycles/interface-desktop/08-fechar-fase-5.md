---
id: UI-TASK-08
---

# UI-TASK-08 — Fechar Fase 5

## Goal

A Fase 5 está verificada: fluxo completo no app com música real escolhida pelo usuário —
abrir, gerar com opções, acompanhar progresso, ver resultados e exportar .gp5 que abre no
TuxGuitar — com confirmação manual do usuário; checks e gates da fase verdes; README raiz
atualizado (seção do app desktop com screenshot).

## Escopo

- In: rodada e2e com música real no app (frio e quente); confirmação do usuário (TuxGuitar);
  checks da Fase 5 do profile; README raiz; probes e suíte Python intactos.
- Out: distribuição pública dos pacotes; v2.

## Done criteria

- [x] Fluxo completo com música real no app: frio e quente, tempos anotados nas Notes com como
      foram medidos; usuário confirma o .gp5 no TuxGuitar (registrado nas Notes).
- [x] Todos os checks da Fase 5 do profile passam.
- [x] `.venv/bin/python scripts/probe_e2e_export.py` e `scripts/probe_e2e_sample.py` saem 0.
- [x] README raiz tem a seção do app desktop (como rodar/instalar) com screenshot.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-FMVP-006): números medidos vão ao README neste mesmo item.

**Rodada real (2026-10-29), AppImage de UI-TASK-07** (`desktop/src-tauri/target/release/bundle/appimage/tabgen-studio_0.1.0_amd64.AppImage`),
Xvfb `:99`, `env -i` + `XDG_DATA_HOME`/`XDG_CONFIG_HOME` novos, pesos no `~/.cache` normal.
Música escolhida pelo usuário: `out/audio/wonderwall.mp3` (60,0 s por `ffprobe … format=duration`),
copiada para pasta nova (cache `.tabgen/` vazio). Fluxo: Início → "Escolher arquivo…" (diálogo GTK) →
`1:00 MP3 · 48 kHz · estéreo` → Gerar tab → painel: aço, capo casa 2, riley, técnicas, gp5 → Gerar.
- Fria: app mostra "Concluído 44,0 s", 10 estágios 100 % (evidencias/08-real-fria-rodando.png,
  08-real-fria.png); polling externo do `.gp5` deu 43,7 s. Tom A major; guitarra 853 notas, 44 sem
  casa, slide 5; baixo 86 notas, 3 sem casa.
- Quente: "Concluído (cache) 0,2 s", todos os estágios "cache" (evidencias/08-real-quente.png).
- Aba Tablatura com prévia ASCII (evidencias/08-real-tablatura.png → `docs/img/tabgen-studio.png`).
- `guitarpro.parse(wonderwall.gp5)` → `guitar [64, 59, 55, 50, 45, 40] capo 2 program 25`,
  `bass [43, 38, 33, 28] capo 0 program 33`, 39 compassos cada.
- **Confirmação do usuário (2026-10-29): `out/desktop-e2e/wonderwall.gp5` abriu ok no TuxGuitar.**

**Checks da Fase 5 (profile).**
- `printf '{"cmd":"doctor","args":{}}\n' | .venv/bin/python -m tabgen.worker` → exit 0, 1 linha,
  JSON válido, `type: result`.
- `cd desktop && npm run build` → 0; `npm run typecheck` → 0.
- App (AppImage): barras por estágio real e cache em 0,2 s (< 5 s) — acima e em UI-TASK-07.
- `.gp5` do app reabre com `guitarpro.parse` (guitar, bass) — acima.
- `grep -rnE "import typer|import rich|print\(" tabgen/core/ | wc -l` → 0.

**Probes e suíte.** `.venv/bin/python scripts/probe_e2e_export.py` → exit 0 (15 s), `PASS: export exit 0
for gp5/musicxml/ascii; …cached rerun mentioned 'cache hit' in 0.24 s…`.
`.venv/bin/python scripts/probe_e2e_sample.py` → exit 0 (10 s), `PASS: transcribe exit 0; both .mid
written…`. `.venv/bin/pytest -q` → `260 passed`; `.venv/bin/ruff check .` → `All checks passed!`.

**README raiz.** Seção "Desktop app (tabgen Studio)" com screenshot (`docs/img/tabgen-studio.png`),
build e configuração do Python; Usage aponta para ela; "Expected runtimes" ganhou as linhas do app
(44 s fria / 0,2 s quente, 1 min, riley, capo 2) com como foram medidas.

## Execution Log
