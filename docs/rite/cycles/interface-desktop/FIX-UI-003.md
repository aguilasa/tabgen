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

## Fix

<!-- Where the change goes. If the defect is in generated output, the fix goes in the generator. -->

Ao fechar a janela / sair (`RunEvent::ExitRequested` ou `WindowEvent::CloseRequested`), percorrer `Jobs` e mandar `killpg` SIGTERM→SIGKILL em cada grupo, reaproveitando a lógica de `cancel_worker`.

## Arquivos

- `desktop/src-tauri/src/lib.rs`

## Verificação

<!-- Command(s) that turn red before the fix and green after it. -->

Mesmo roteiro da Evidência (só em Xvfb, nunca no display do usuário): após fechar a janela, `ps -eo args | grep -c '[-]m tabgen.worker'` → `0` em até 3 s.

## Execution Log
