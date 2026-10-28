---
id: UI-TASK-01
---

# UI-TASK-01 — Implementar worker NDJSON sobre o core

## Goal

Existe `tabgen/worker/` (camada fina como a `cli/`, fora do `core/`): `python -m tabgen.worker`
lê UMA requisição NDJSON em stdin (`{"cmd": "doctor"|"analyze"|"transcribe"|"tablature",
"args": {…}}`, args espelhando os parâmetros das funções `run_*`/`run_checks`), emite
`{"type":"progress","stage","pct"}` por evento do `on_progress`, termina com
`{"type":"result",…to_dict()…}` ou `{"type":"error","kind","message"}` e sai 0/1. O resultado de
`tablature` inclui a prévia de `render_ascii_tab()`. É a fronteira testável entre a UI e o core.

## Escopo

- In: parse/validação da requisição (cmd desconhecido ou args inválidos → error + exit 1);
  mapeamento args → `run_*` (afinações via `resolve_tuning`, formato via `resolve_export_format`);
  serialização dos summaries (`to_dict`) + campo `ascii_preview`; stdout exclusivo para NDJSON
  (logs em stderr); testes com funções de estágio injetadas (padrão dos testes do pipeline).
- Out: qualquer código Tauri/JS (TASK-02+); cancelamento cooperativo (cancelar = matar o
  processo, decisão da spec).

## Done criteria

- [ ] `printf '{"cmd":"doctor","args":{}}\n' | .venv/bin/python -m tabgen.worker` imprime só
      linhas JSON válidas e termina com `{"type":"result",…}`; exit 0.
- [ ] Teste com stages injetados: requisição `tablature` emite progress para cada estágio real
      (`separation`…`export`), pct final 100 em todos, e o result reabre com `json.loads` e contém
      `ascii_preview` não vazio.
- [ ] Teste: cmd desconhecido e args inválidos produzem `{"type":"error",…}` e exit 1.
- [ ] Teste: nada além de NDJSON sai no stdout (stderr livre).
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada (worker fora do core).
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Um job por processo (spec, seção 3). Pitfall herdado: convenção de cada campo do protocolo fica
em docstring/README do módulo, não em prosa de tarefa.

## Execution Log
