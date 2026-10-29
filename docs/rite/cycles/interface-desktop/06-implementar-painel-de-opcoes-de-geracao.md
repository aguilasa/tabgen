---
id: UI-TASK-06
---

# UI-TASK-06 — Implementar painel de opções de geração

## Goal

O painel "Gerar tab ▶" existe conforme o protótipo: instrumentos (guitarra/baixo), afinação da
guitarra (presets reais + custom com validação), afinação do baixo (incl. five-string), capo
0–12, tipo de guitarra (elétrica/nylon/aço), transcriber (riley/basic-pitch), técnicas on/off,
device (auto/cuda/cpu), caminho de saída com formato pelo sufixo ou seletor. As escolhas vão na
requisição NDJSON e ficam lembradas por música.

## Escopo

- In: presets de `TUNING_PRESETS` expostos pelo worker (cmd auxiliar ou constante no payload do
  doctor — decidir na execução); validação do custom espelhando `resolve_tuning` (erro do worker
  exibido no campo); persistência das últimas opções; estimativa de tempo exibida (fria vs cache).
- Out: perfis de preset salvos pelo usuário (v2).

## Done criteria

- [ ] Gerar com drop-d + capo 2 + nylon produz .gp5 cuja afinação/capo/programa GM conferem
      (reaberto via guitarpro no teste do worker ou CLI).
- [ ] Afinação custom inválida (ex.: ordem decrescente) mostra o erro do worker no campo, sem
      rodar o pipeline.
- [ ] Trocar transcriber invalida o cache (execução seguinte fria nos estágios de transcrição).
- [ ] Reabrir a música mostra as últimas opções usadas.
- [ ] `npm run build` e typecheck do frontend saem 0.

## Notes

Fonte única dos presets é o core (worker expõe) — nada de duplicar listas de afinação no JS.
Pitfall herdado: comparar valores parseados, não strings.

Da UI-TASK-04: o botão "Gerar tab ▶" chama `useTablatureRun.start(path)`, que monta os args com `tablatureArgs(path, prefs)` em `desktop/src/lib/run.ts`; o drawer deve estender essa função ou dar um argumento de opções ao `start`.

Da UI-TASK-05: `tablatureArgs(path, prefs)` em `desktop/src/lib/run.ts` monta os args e os
guarda em `RunState.args`; exports (`useExports`) e os jobs de detalhe (`detailArgs`) os
reaproveitam — estender `tablatureArgs` com instrumentos/afinações/capo/técnicas/guitar_type/saída
propaga para eles. Formato→sufixo: `exportPath`/`EXPORT_SUFFIX` em `run.ts`. Comando de presets:
`COMMANDS` e `_HANDLERS` em `tabgen/worker/__init__.py` e `WorkerCmd` em `worker.ts`;
`tracks[].tuning_name` já casa com `TUNING_PRESETS`.

## Execution Log
