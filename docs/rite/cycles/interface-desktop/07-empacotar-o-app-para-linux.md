---
id: UI-TASK-07
---

# UI-TASK-07 — Empacotar o app para Linux

## Goal

O app empacota para Linux: `tauri build` gera .deb e AppImage que instalam/rodam numa máquina
com o tabgen instalado em venv; o app embala só o frontend + binário Tauri e localiza o Python
como no dev (preferências), com a tela Ambiente orientando quando faltar algo. README do
`desktop/` documenta build e requisitos.

## Escopo

- In: configuração de bundle do Tauri (ícone, nome, versão); verificação do fluxo
  "Python ausente → orientação"; `desktop/README.md` (build, requisitos, onde configurar o
  Python); entrada no README raiz apontando para o app.
- Out: CI; instaladores Windows/macOS; bundling do Python (fora da v1).

## Done criteria

- [x] `cd desktop && npm run tauri build` sai 0 e gera `.deb` e `.AppImage` (caminhos e tamanhos
      nas Notes com o comando).
- [x] AppImage roda nesta máquina: abre, Ambiente verde, pipeline da amostra funciona
      (screenshot nas Notes).
- [x] Com preferência de Python apontando para caminho inexistente, o AppImage abre e orienta em
      vez de quebrar.
- [x] `desktop/README.md` existe com build + requisitos; README raiz linka.

## Notes

Tamanho do bundle e tempo de build vão nas Notes com os comandos (regra do CLAUDE.md sobre
números).

**Build (2026-10-29).** `cd desktop && npm run tauri build` → exit 0; 274 s na primeira (inclui o
download de `linuxdeploy`/AppRun pelo bundler), 202 s no rebuild após mudar `lib.rs` (medido com
`date +%s` antes/depois). Saída do bundler:
`deb/tabgen-studio_0.1.0_amd64.deb (1.92 MiB)` e `appimage/tabgen-studio_0.1.0_amd64.AppImage
(80.11 MiB)` em `desktop/src-tauri/target/release/bundle/`. `dpkg-deb -f …deb Depends` →
`ffmpeg, libwebkit2gtk-4.1-0, libgtk-3-0`. Bundle: só `deb` + `appimage`, categoria Music,
ícone novo (`desktop/src-tauri/icons/src/icon.svg` → `npx tauri icon`).

**Controle: AppImage quebrava o worker.** Primeiro build, rodado em Xvfb `:99` com XDG isolado:
"Ambiente com falha · Python", `WorkerCrash … exit code 1` com `sys.prefix = '/tmp/.mount_tabgen…/usr/'`
(evidencias/07-appimage-env-vazado-antes.png). Causa: o AppRun exporta `PYTHONHOME`,
`PYTHONPATH`, `LD_LIBRARY_PATH`, `GTK_*` etc. apontando para a imagem (`/proc/<pid>/environ`), e os
filhos herdavam. Correção em `desktop/src-tauri/src/lib.rs` (fora dos `files` declarados,
`--amend-files`): `host_command()` remove as variáveis cujo valor contém `$APPDIR` e limpa as
entradas da imagem de `PATH`/`XDG_DATA_DIRS`; usado no worker, no reaper, em `ffprobe` e
`xdg-open`. Teste `appimage_env_is_taken_out_of_child_processes` (`cargo test` → 1 passed). O
`current_dir` do worker agora só é aplicado se o checkout de build existir (em outra máquina o
`tabgen` instalado no venv basta; `cd /tmp && .venv/bin/python -c "import tabgen"` ok).

**AppImage após a correção** (Xvfb `:99`, `env -i` + XDG isolado, amostra
`ffmpeg -f lavfi -i sine=frequency=220:duration=10 -q:a 2 sample.mp3`, mesma de
`scripts/probe_e2e_worker.py`): Ambiente verde, 5 checks ✓ (evidencias/07-appimage-ambiente.png);
abrir pelo diálogo GTK mostra `0:10 MP3 · 44,1 kHz · mono` (ffprobe ok); Gerar → "Concluído 53,9 s",
10 estágios 100 % (evidencias/07-appimage-pipeline-fria.png). Os 53,9 s incluem baixar pesos para o
cache isolado (`du -sh x07/cache/huggingface` → 469M), não é o tempo normal. Segunda execução:
"Concluído (cache) 0,2 s" (evidencias/07-appimage-pipeline-cache.png).
`guitarpro.parse(sample.gp5).tracks` → `['guitar', 'bass']`.

**Python inexistente.** Interpretador = `/opt/nao-existe/bin/python`, app fechado e reaberto: abre,
cabeçalho "Ambiente com falha · Python", Ambiente mostra `SpawnError: cannot start Python at
'/opt/nao-existe/bin/python': No such file or directory (os error 2)` + orientação
(evidencias/07-appimage-python-ausente.png).

**Docs.** `desktop/README.md` (requisitos, onde configurar o Python, dev, build com tamanhos/tempos,
instalação, nota do AppRun). README raiz: árvore de arquitetura com `worker/` e `desktop/`,
introdução e Usage linkam `desktop/README.md`.

Sweep (`may come later, desktop later, repo_root, tauri build, AppImage, Interpretador Python`):
nada obsoleto (o "may come later" da árvore do README raiz foi corrigido nesta tarefa).

Nota: o padrão vazio do interpretador (`.venv` do checkout de build) só existe na máquina de
build; documentado no `desktop/README.md`, a tela já orienta quando falta.

## Execution Log
