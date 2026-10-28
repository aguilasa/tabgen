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

- [x] `printf '{"cmd":"doctor","args":{}}\n' | .venv/bin/python -m tabgen.worker` imprime só
      linhas JSON válidas e termina com `{"type":"result",…}`; exit 0.
- [x] Teste com stages injetados: requisição `tablature` emite progress para cada estágio real
      (`separation`…`export`), pct final 100 em todos, e o result reabre com `json.loads` e contém
      `ascii_preview` não vazio.
- [x] Teste: cmd desconhecido e args inválidos produzem `{"type":"error",…}` e exit 1.
- [x] Teste: nada além de NDJSON sai no stdout (stderr livre).
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada (worker fora do core).
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Um job por processo (spec, seção 3). Pitfall herdado: convenção de cada campo do protocolo fica
em docstring/README do módulo, não em prosa de tarefa.

Protocolo (chaves de `args` por `cmd`, formato de cada linha) documentado na docstring de
`tabgen/worker/__init__.py`. Decisões de implementação:

- Só `DoctorReport` tem `to_dict()`; os summaries do pipeline são dataclasses e saem com
  `dataclasses.asdict` (mesmo contrato do `_JsonMixin.to_dict` dos modelos).
- `analyze` não escreve `.analysis.json` (isso é da CLI); o resultado já carrega `result`.
- Requisição inválida → `kind: "RequestError"`; erro do core mantém o nome (ex. `PipelineError`
  para formato de saída desconhecido).
- Stdout isolado em dois níveis: `run()` redireciona `sys.stdout` para stderr durante o job;
  `__main__` duplica o fd 1 para o stream NDJSON e aponta o fd 1 para stderr (bibliotecas nativas,
  subprocessos). `json.dumps(allow_nan=False)`: NaN vira erro em vez de JSON inválido.

Verificação (HEAD do work commit):

- `printf '{"cmd":"doctor","args":{}}\n' | .venv/bin/python -m tabgen.worker 2>/dev/null | python3 -c 'import sys,json; L=[json.loads(l) for l in sys.stdin]; print(len(L), L[-1]["type"], L[-1]["ok"])'`
  → `1 result True`, exit 0.
- `.venv/bin/pytest -q tests/test_worker.py` → `16 passed` (tablature com stages injetados:
  todos os estágios de `_tablature_stages` + `export` chegam a 100, `ascii_preview` não vazio;
  10 requisições inválidas → `RequestError`, exit 1; subprocesso doctor só NDJSON).
- Controle do teste de stdout: trocando o `redirect_stdout` por `nullcontext` →
  `FAILED tests/test_worker.py::test_stage_prints_go_to_stderr_not_the_stream`; restaurado.
  Ruído em fd 1 (`os.write(1, …)` num handler, via `__main__.main`) → stdout só
  `{"type": "result", "ok": true}`.
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (rc 1).
- `.venv/bin/pytest -q` → `237 passed`; `.venv/bin/ruff check .` → `All checks passed!`.

## Execution Log

- **Closed** — commit `455268e` (2026-10-28): feat(worker): add NDJSON worker over the core pipeline
  - Files (`git show --name-status 455268e`):
    - `M docs/rite/cycles/interface-desktop/01-implementar-worker-ndjson-sobre-o-core.md`
    - `A tabgen/worker/__init__.py`
    - `A tabgen/worker/__main__.py`
    - `A tests/test_worker.py`
