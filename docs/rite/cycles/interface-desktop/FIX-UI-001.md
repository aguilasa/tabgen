---
id: FIX-UI-001
---

# FIX-UI-001 — Verificar persistência das preferências após reiniciar o app

Origin: [UI-TASK-02](/docs/rite/cycles/interface-desktop/02-criar-scaffold-tauri-com-sidecar-e-tela-ambiente.md)

## Problem

O objetivo da UI-TASK-02 inclui "padrões persistidos (device, transcriber, pasta de saída)", mas a
persistência entre execuções do app nunca foi observada: a tarefa fechou com os critérios
(que não a exigem) e a verificação ficou pendente. As preferências vão para `localStorage`
(`desktop/src/lib/prefs.ts`, chave `tabgen.prefs`); não se sabe se o WebKitGTK do Tauri mantém
esse armazenamento ao reiniciar o app.

## Evidência

<!-- The exact command and its output that shows the problem. Whoever fixes this reproduces it first. -->

```text
$ cd desktop && npm run tauri dev   # escolher Dispositivo = cpu na tela Ambiente, fechar a janela
$ cd desktop && npm run tauri dev   # relançado: a janela ficou "Map State: IsUnMapped" (xwininfo);
                                    # não deu para ver se "cpu" continuou selecionado
```

## Root cause

## Fix

<!-- Where the change goes. If the defect is in generated output, the fix goes in the generator. -->

## Arquivos

- `desktop/src/lib/prefs.ts` (se `localStorage` não persistir: trocar por `tauri-plugin-store`)

## Verificação

Abrir o app, mudar Dispositivo para `cpu` e o Interpretador Python, fechar e reabrir: os dois
valores voltam iguais (screenshot em `evidencias/`).

## Execution Log
