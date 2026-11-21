---
id: UI-TASK-04
---

# UI-TASK-04 — Implementar workspace com progresso por estágio e cancelamento

## Goal

O workspace existe conforme o protótipo: cabeçalho com "Gerar tab ▶", cartões de estágio
(pendente/cache/rodando/ok/erro) e painel de execução com uma barra por estágio real do core
(`separation`…`export`), alimentadas pelos eventos NDJSON do worker; "Cancelar" encerra o
processo worker e marca o estado; erro de estágio aparece com a mensagem da exceção.

## Escopo

- In: spawn do worker com a requisição `tablature` (opções padrão nesta task); consumo dos
  eventos progress em tempo real; estados dos cartões derivados dos estágios; kill do processo no
  cancelar; exibição de `{"type":"error"}` com kind/message; estado "cache hit" (estágios a 100
  de imediato).
- Out: abas de resultados (05); painel de opções (06 — aqui o botão roda com defaults).

## Done criteria

- [x] Com a amostra sintética fria, as barras avançam na ordem real dos estágios e terminam
      todas em 100; resultado aparece (screenshot nas Notes).
- [x] Segunda execução (quente) mostra cache em <5 s.
- [x] Cancelar durante a separação encerra o processo (worker some do `ps`) e o estado fica
      "cancelado"; rodar de novo reusa o cache dos estágios concluídos.
- [x] Erro simulado (ex.: caminho de Python sem madmom) aparece com kind e mensagem.
- [x] `npm run build` e typecheck do frontend saem 0.

## Notes

Mapa estágio→barra segue a ordem de `_tablature_stages` (worker repassa os nomes reais;
nada hardcoded fora da ordem de exibição).

Da UI-TASK-03: `desktop/src/screens/Musica.tsx` é cabeçalho + placeholder; após um pipeline,
atualizar `processed_at` e `artifacts` da entrada em `desktop/src/lib/recents.ts` (pelo caminho;
ainda não há função para isso). Para abrir uma música sem o picker num teste headless, há
`TABGEN_OPEN=<caminho>` (só debug). Verificação de GUI só em Xvfb, nunca no display do usuário.

Implementado por rite-worker (onda 2 do batch com UI-TASK-03).

Decisões:

- Cancelar (`lib.rs`): `run_worker` aceita `job_id` opcional (doctor segue sem); o worker nasce em
  grupo próprio (`process_group(0)`), um mapa `Jobs` guarda pid e flag; `cancel_worker` manda
  `killpg` SIGTERM e SIGKILL após 2 s se ainda registrado. `WorkerExit.cancelled` vira
  `WorkerError` kind `Cancelled` no `worker.ts`. Dependência nova: `libc = "0.2"`.
- Estado da execução (`lib/run.ts`, `useTablatureRun` no App): um job por vez; barras criadas
  conforme os eventos chegam, ordenadas só pela ordem de exibição; estágio cujo primeiro evento
  já é 100 conta como "cache" (`export` nunca, o core sempre o refaz). Cartões derivam dos
  estágios: pendente/rodando/ok/cache/erro/cancelado.
- Defaults vêm das prefs (transcriber, device se não "auto", `outputDir` → `<dir>/<stem>.gp5`).
  Ao concluir, `markProcessed` em `recents.ts` grava `processed_at` e `artifacts`.

Verificação (Xvfb `:99`, binário debug com `XDG_DATA_HOME` isolado, cliques por xdotool no `:99`):

- Frio: amostra nova `ffmpeg -y -f lavfi -i sine=frequency=220:duration=10 -q:a 2 sample.mp3`
  em diretório novo → barras na ordem separation … export, todas 100%, "Concluído 14,3 s",
  cartões ok (A major / riley / sample.gp5) (`evidencias/04-frio-progresso.png`,
  `evidencias/04-frio-resultado.png`).
- Quente: segunda execução → "Concluído (cache) 0,2 s" (cronômetro da UI, `performance.now()`
  do clique ao resultado); processo worker sumiu do `ps` 0,245 s após o clique; nove barras
  "cache" (`evidencias/04-quente-cache.png`). Número medido na GUI, sem probe versionado — ver
  FIX aberto para o probe.
- Cancelar na separação (wonderwall.mp3 copiado para diretório novo): `ps -eo args | grep -c
  '[-]m tabgen.worker'` → 0 em +0,5 s; "Cancelado", cartão Separação "cancelado"
  (`evidencias/04-cancelado-separacao.png`). Cancelado de novo já na análise (após
  `.tabgen/separation-*.json` existir) → grupo do processo vazio; nova execução mostra
  separation "cache" e conclui em 27,6 s (`evidencias/04-cancelado-analise.png`,
  `evidencias/04-cache-apos-cancelar.png`, `evidencias/04-rerun-concluido.png`).
- Erro: prefs com `/usr/bin/python3` (3.12 sem dependências) → "Falhou", cartão Separação "erro",
  "ModuleNotFoundError: No module named 'soundfile'" (`evidencias/04-erro.png`).
- `npm run typecheck` rc 0; `npm run build` → `✓ built`; `cargo clippy -q` sem saída;
  `cargo fmt --check` rc 0; `.venv/bin/pytest -q` → `237 passed`; `ruff check .` limpo.
- Não exercitado: kill de processos filhos reais do worker (Demucs roda no mesmo processo);
  fechar a janela com job rodando deixa o worker órfão (fix aberto).

Para UI-TASK-05: `RunState.result` traz o `TablatureResult` completo (scores, beat_grids,
key_check, unassigned, ascii_preview, output_path, format, cache_hit). Para UI-TASK-06:
estender `tablatureArgs(path, prefs)` em `lib/run.ts` ou dar opções a `useTablatureRun.start`.

## Execution Log

- **Closed** — commit `72ebb52` (2026-10-28): feat(desktop): run tablature from the workspace with live per-stage progress, cancel and errors
  - Files (`git show --name-status 72ebb52`):
    - `M desktop/src-tauri/Cargo.lock`
    - `M desktop/src-tauri/Cargo.toml`
    - `M desktop/src-tauri/src/lib.rs`
    - `M desktop/src/App.css`
    - `M desktop/src/App.tsx`
    - `A desktop/src/components/Pipeline.tsx`
    - `M desktop/src/lib/recents.ts`
    - `A desktop/src/lib/run.ts`
    - `M desktop/src/lib/worker.ts`
    - `M desktop/src/screens/Musica.tsx`
    - `M docs/rite/cycles/interface-desktop/04-implementar-workspace-com-progresso-por-estagio.md`
    - `M docs/rite/cycles/interface-desktop/05-implementar-abas-de-resultados-com-previa-ascii.md`
    - `M docs/rite/cycles/interface-desktop/06-implementar-painel-de-opcoes-de-geracao.md`
    - `A docs/rite/cycles/interface-desktop/evidencias/04-cache-apos-cancelar.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/04-cancelado-analise.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/04-cancelado-separacao.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/04-erro.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/04-frio-progresso.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/04-frio-resultado.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/04-quente-cache.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/04-rerun-concluido.png`
  - **Files amended** — added to `files`:
    - `desktop/src/lib/recents.ts`
    - `docs/rite/cycles/interface-desktop/05-implementar-abas-de-resultados-com-previa-ascii.md`
    - `docs/rite/cycles/interface-desktop/06-implementar-painel-de-opcoes-de-geracao.md`
- **Reviewed** (2026-10-29) at `8078ed8`: FIX-UI-006
