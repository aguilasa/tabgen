---
id: FIX-UI-003
---

# FIX-UI-003 — Encerrar workers em andamento ao fechar a janela do app

Origin: [UI-TASK-04](/docs/rite/cycles/interface-desktop/04-implementar-workspace-com-progresso-por-estagio.md)

## Problem

<!-- What is wrong, stated as an observable fact. -->

Fechar a janela do tabgen Studio com um job de tablatura rodando não encerra o worker: o mapa `Jobs` de `desktop/src-tauri/src/lib.rs` só é limpo no fim do job e nada mata os grupos de processo ao sair, então `python -m tabgen.worker` continua (GPU ocupada, escrevendo saída) sem UI. Relatado pelo worker da UI-TASK-04; não reproduzido ainda.

## Evidência

<!-- The exact command and its output that shows the problem. Whoever fixes this reproduces it first. -->

```text
$ # Xvfb :99, app debug, abrir música longa (ex.: wonderwall.mp3 copiada para dir novo), Gerar tab
$ xdotool --display :99 ... windowclose <janela>   # durante a separação
$ ps -eo args | grep -c '[-]m tabgen.worker'
1   # esperado após o fix: 0
```

## Root cause

`run()` não registrava nenhum handler de saída: nada percorria `Jobs` ao fechar a janela, e o
fechamento bruto da janela (XDestroyWindow) aborta o processo da UI via GDK antes de qualquer
evento do Tauri, então nenhum caminho matava os grupos de processo dos workers.

## Fix

<!-- Where the change goes. If the defect is in generated output, the fix goes in the generator. -->

Ao fechar a janela / sair (`RunEvent::ExitRequested` ou `WindowEvent::CloseRequested`), percorrer `Jobs` e mandar `killpg` SIGTERM→SIGKILL em cada grupo, reaproveitando a lógica de `cancel_worker`.

## Arquivos

- `desktop/src-tauri/src/lib.rs`

## Verificação

<!-- Command(s) that turn red before the fix and green after it. -->

Mesmo roteiro da Evidência (só em Xvfb, nunca no display do usuário): após fechar a janela, `ps -eo args | grep -c '[-]m tabgen.worker'` → `0` em até 3 s.

## Execution Log

- 2026-10-28 — Triagem (agente rite:rite-reproducer, Xvfb :99): REPRODUCED. Com job de tablatura
  em separação (sine de 4 min, cache frio), `xdotool windowclose` matou o tabgen-studio mas
  `ps -eo pid,pgid,args | grep '[-]m tabgen.worker'` passou de 1 (antes) para 2 (depois, +5 s):
  worker órfão (PPID reparentado) + filho em grupo próprio, vivos ~1 min até kill manual.
  Estaticamente `lib.rs` confirma: `run_worker` usa `.process_group(0)` (linha 104), `Jobs` só
  drena no fim do job (122-124) ou via `cancel_worker`, e `run()` (283-298) não registra
  `on_window_event`/`RunEvent::ExitRequested`. Screenshots em scratchpad ui003/shot{1,2}.png.
- 2026-10-28 — Fix (agente executor, Xvfb :99). Mudanças em `desktop/src-tauri/src/lib.rs`:
  (1) `run()` passou de `.run(generate_context!())` para `.build(...).run(|app, event| ...)`
  tratando `RunEvent::ExitRequested` (dispara tanto ao fechar a última janela quanto em exit
  explícito) e chamando o novo helper `kill_all_jobs`, que percorre `Jobs` e manda SIGTERM a
  cada grupo, espera `CANCEL_GRACE` (2 s) bloqueando — thread em background morreria junto com
  o processo — e manda SIGKILL no que sobrou (ESRCH é inofensivo); (2) descoberto no teste que
  `xdotool windowclose` faz `XDestroyWindow` e o GDK aborta o processo com `BadDrawable`
  (dev.log) antes de qualquer evento do Tauri rodar — equivalente a kill -9 da UI, nenhum
  handler in-process cobre esse caminho —, então `run_worker` ganhou um reaper por job
  (`spawn_reaper`/`release_reaper`): um `sh` mínimo bloqueado em `read` num pipe do processo
  da UI; morte da UI por qualquer via fecha o pipe e o reaper manda SIGTERM→(2 s)→SIGKILL no
  grupo; no fim normal do job `release_reaper` escreve "done" e colhe o `sh` (sem matar pgid
  reutilizado). Medições (sine 4 min, cache frio, dir novo por rodada): fechamento bruto
  (`xdotool windowclose`): antes 1 worker (pid=pgid 91441, separation 3%), +5 s → `grep -c` = 0,
  reaper e app encerrados; fechamento gracioso (WM_DELETE_WINDOW via ctypes, caminho real do
  botão fechar): antes 1 worker (92619), app saiu limpo (exit 0, sem BadDrawable), +5 s →
  `grep -c` = 0. Controle vermelho: mesma janela windowclose antes do fix nesta sessão deixou
  o worker 87542 vivo (+5 s → 1). Build `cargo build` e `cargo clippy` limpos; `ruff` ok e
  `pytest` 237 passed (Python intocado). Screenshots/logs em scratchpad ui003fix/.
- 2026-10-28 — Verificação final na árvore do commit (FIX-UI-004 em stash): `cargo build
  --manifest-path desktop/src-tauri/Cargo.toml` → Finished dev profile; `.venv/bin/ruff check .`
  → All checks passed!; `.venv/bin/pytest -q` → 237 passed; `rite gates --id FIX-UI-003` →
  passed. Medições de GUI (ps = 0 nos dois caminhos de fechamento, controle vermelho = 1) são
  da rodada do executor nesta mesma árvore de `lib.rs`, registradas acima.
