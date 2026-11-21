---
id: UI-TASK-02
---

# UI-TASK-02 — Criar scaffold Tauri com sidecar e tela Ambiente

## Goal

Existe `desktop/` com app Tauri 2 + React + Vite que sobe (`npm run tauri dev`), localiza o
interpretador Python configurado (padrão: `.venv/bin/python` do repo; configurável na UI), roda o
worker como processo filho e mostra a tela Ambiente: os 5 checks do doctor com detalhe, botão
"verificar de novo", badge de resumo na barra do app e padrões persistidos (device, transcriber,
pasta de saída). Primeira fatia de ponta a ponta UI→worker→core.

## Escopo

- In: scaffold Tauri 2 (React+Vite, TypeScript); comando Rust/JS que spawna
  `python -m tabgen.worker` e entrega as linhas NDJSON ao frontend; store de preferências
  (caminho do Python, device, transcriber, pasta de saída); tela Ambiente conforme protótipo;
  tema claro/escuro do sistema.
- Out: demais telas (03–06); empacotamento (07); bundling do Python (fora da v1).

## Done criteria

- [x] `cd desktop && npm run tauri dev` abre o app; a tela Ambiente lista os 5 checks reais com
      detalhe (GPU/VRAM, versão do madmom, disco) — screenshot nas Notes.
- [x] Com caminho de Python inválido nas preferências, a tela mostra erro orientando e o badge
      fica vermelho (screenshot).
- [x] `cd desktop && npm run build` sai 0; lint/typecheck do frontend (`npm run lint` ou `tsc
      --noEmit`) sai 0.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` continuam verdes (nada do Python mudou).

## Notes

Referência visual: protótipo aprovado (profile, Sources of truth). `desktop/` tem seu próprio
toolchain (npm); gates Python do repo não cobrem o frontend — checks do frontend entram nos done
criteria de cada task.

Toolchain instalada nesta tarefa (autorizada pelo usuário em 2026-10-28): libs Tauri via apt
(`libwebkit2gtk-4.1-dev`, `libsoup-3.0-dev`, `libayatana-appindicator3-dev`, `librsvg2-dev`,
`libxdo-dev`, `libssl-dev`, `build-essential`) e Rust 1.99.1 via `mise use -g rust@stable`.

Implementação:

- Scaffold `npm create tauri-app@4 desktop -- --template react-ts`; removidos README, assets
  e o plugin opener (não usado). App renomeado `tabgen-studio`, janela "tabgen Studio".
- `src-tauri/src/lib.rs`: comandos `default_python` (`<repo>/.venv/bin/python`, raiz vinda de
  `CARGO_MANIFEST_DIR`) e `run_worker` (spawna `python -m tabgen.worker` com cwd na raiz do repo,
  escreve a requisição no stdin, repassa cada linha do stdout por `Channel`, devolve exit code e
  cauda do stderr). Falha de spawn vira `SpawnError` no `lib/worker.ts`; processo que termina sem
  linha final vira `WorkerCrash`.
- Preferências em `localStorage` (`lib/prefs.ts`): Python (vazio = .venv do repo), device,
  transcriber, pasta de saída. Tema segue o sistema; botão alterna sistema/escuro/claro.
- `desktop/.npmrc` com `legacy-peer-deps=true`: o npm 10.8.2 quebra com
  `Cannot read properties of null (reading 'edgesOut')` resolvendo peers opcionais do template
  (vitest/happy-dom/jsdom); com a flag instala e `npm ls --depth=0` sai sem peer faltando.
- Arquivos além da lista declarada: o resto do scaffold (Cargo.toml/lock, build.rs,
  capabilities, ícones, index.html, main.tsx, App.css, tsconfig, vite.config, lockfile, .gitignore,
  .npmrc) e as evidências em `evidencias/`; registrados com `--amend-files`.

Verificação (HEAD do work commit):

- `cd desktop && npm run tauri dev` abre a janela; a tela lista os 5 checks reais —
  `evidencias/02-ambiente-ok.png`: torch+cuda "RTX 3060 Laptop GPU (5.7 GB VRAM)", madmom
  0.17.dev0, disco 896.1 GB livres; badge verde "Ambiente ok · RTX 3060 Laptop GPU · cuda".
- Python `/opt/nao-existe/bin/python` nas preferências → `evidencias/02-ambiente-python-invalido.png`:
  "SpawnError: cannot start Python at '/opt/nao-existe/bin/python': No such file or directory",
  texto orientando, badge vermelho "Ambiente com falha · Python". Com `/usr/bin/python3` (3.12, sem
  torch/madmom) o doctor roda e marca python, torch+cuda e madmom com ✗ (badge vermelho).
- `npm run build` → `✓ built`, rc 0; `npm run typecheck` (`tsc --noEmit`) rc 0;
  `cargo clippy -q` rc 0 sem avisos.
- `.venv/bin/pytest -q` → `237 passed`; `.venv/bin/ruff check .` → `All checks passed!`.
- Não verificado: persistência das preferências após reiniciar o app (a janela relançada não
  mapeou no X11 durante o teste; não é critério desta tarefa).

## Execution Log

- **Closed** — commit `b8bd761` (2026-10-28): feat(desktop): scaffold Tauri app with worker sidecar and Ambiente screen
  - Files (`git show --name-status b8bd761`):
    - `A desktop/.gitignore`
    - `A desktop/.npmrc`
    - `A desktop/index.html`
    - `A desktop/package-lock.json`
    - `A desktop/package.json`
    - `A desktop/src-tauri/.gitignore`
    - `A desktop/src-tauri/Cargo.lock`
    - `A desktop/src-tauri/Cargo.toml`
    - `A desktop/src-tauri/build.rs`
    - `A desktop/src-tauri/capabilities/default.json`
    - `A desktop/src-tauri/icons/128x128.png`
    - `A desktop/src-tauri/icons/128x128@2x.png`
    - `A desktop/src-tauri/icons/32x32.png`
    - `A desktop/src-tauri/icons/Square107x107Logo.png`
    - `A desktop/src-tauri/icons/Square142x142Logo.png`
    - `A desktop/src-tauri/icons/Square150x150Logo.png`
    - `A desktop/src-tauri/icons/Square284x284Logo.png`
    - `A desktop/src-tauri/icons/Square30x30Logo.png`
    - `A desktop/src-tauri/icons/Square310x310Logo.png`
    - `A desktop/src-tauri/icons/Square44x44Logo.png`
    - `A desktop/src-tauri/icons/Square71x71Logo.png`
    - `A desktop/src-tauri/icons/Square89x89Logo.png`
    - `A desktop/src-tauri/icons/StoreLogo.png`
    - `A desktop/src-tauri/icons/icon.icns`
    - `A desktop/src-tauri/icons/icon.ico`
    - `A desktop/src-tauri/icons/icon.png`
    - `A desktop/src-tauri/src/lib.rs`
    - `A desktop/src-tauri/src/main.rs`
    - `A desktop/src-tauri/tauri.conf.json`
    - `A desktop/src/App.css`
    - `A desktop/src/App.tsx`
    - `A desktop/src/lib/prefs.ts`
    - `A desktop/src/lib/worker.ts`
    - `A desktop/src/main.tsx`
    - `A desktop/src/screens/Ambiente.tsx`
    - `A desktop/src/vite-env.d.ts`
    - `A desktop/tsconfig.json`
    - `A desktop/tsconfig.node.json`
    - `A desktop/vite.config.ts`
    - `M docs/rite/cycles/interface-desktop/02-criar-scaffold-tauri-com-sidecar-e-tela-ambiente.md`
    - `A docs/rite/cycles/interface-desktop/evidencias/02-ambiente-ok.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/02-ambiente-python-invalido.png`
  - **Files amended** — added to `files`:
    - `desktop/.gitignore`
    - `desktop/.npmrc`
    - `desktop/index.html`
    - `desktop/package-lock.json`
    - `desktop/src-tauri/.gitignore`
    - `desktop/src-tauri/Cargo.lock`
    - `desktop/src-tauri/Cargo.toml`
    - `desktop/src-tauri/build.rs`
    - `desktop/src-tauri/capabilities/default.json`
    - `desktop/src-tauri/icons/128x128.png`
    - `desktop/src-tauri/icons/128x128@2x.png`
    - `desktop/src-tauri/icons/32x32.png`
    - `desktop/src-tauri/icons/Square107x107Logo.png`
    - `desktop/src-tauri/icons/Square142x142Logo.png`
    - `desktop/src-tauri/icons/Square150x150Logo.png`
    - `desktop/src-tauri/icons/Square284x284Logo.png`
    - `desktop/src-tauri/icons/Square30x30Logo.png`
    - `desktop/src-tauri/icons/Square310x310Logo.png`
    - `desktop/src-tauri/icons/Square44x44Logo.png`
    - `desktop/src-tauri/icons/Square71x71Logo.png`
    - `desktop/src-tauri/icons/Square89x89Logo.png`
    - `desktop/src-tauri/icons/StoreLogo.png`
    - `desktop/src-tauri/icons/icon.icns`
    - `desktop/src-tauri/icons/icon.ico`
    - `desktop/src-tauri/icons/icon.png`
    - `desktop/src-tauri/src/lib.rs`
    - `desktop/src/App.css`
    - `desktop/src/main.tsx`
    - `desktop/src/vite-env.d.ts`
    - `desktop/tsconfig.json`
    - `desktop/tsconfig.node.json`
    - `desktop/vite.config.ts`
    - `docs/rite/cycles/interface-desktop/evidencias/02-ambiente-ok.png`
    - `docs/rite/cycles/interface-desktop/evidencias/02-ambiente-python-invalido.png`
- **Reviewed** (2026-10-28) at `8b6b22c`: no finding
