---
id: FMVP-TASK-02
---

# FMVP-TASK-02 — Implementar contratos de estágio e cache em disco

## Goal

Existem as dataclasses que formam os contratos entre os estágios do pipeline
(plano, seção 2): `SeparationResult`, `AnalysisResult`, `NoteEvents`/`Note`, `TabScore`
(esqueleto), todas serializáveis em JSON, e um cache em disco (`.tabgen/` ao lado do áudio)
que grava e recupera resultados por estágio + hash do arquivo de entrada.

## Escopo

- In: `tabgen/core/models.py` (dataclasses + `to_json`/`from_json`), `tabgen/core/cache.py`
  (chave = estágio + sha256 do input + versão do modelo; invalidação por versão),
  tipo de callback de progresso (`ProgressCallback`) em `tabgen/core/pipeline.py`, testes
  de round-trip e de cache hit/miss.
- Out: implementação dos estágios; CLI além do que já existe.

## Done criteria

- [ ] `pytest -q tests/test_models.py tests/test_cache.py` verde: round-trip JSON de cada
      dataclass preserva igualdade; cache miss → grava; segunda chamada → hit sem recompute
      (verificado por contador/mock).
- [ ] Nenhum campo dos contratos usa tipos não serializáveis (teste serializa com `json.dumps`
      sem encoder custom falhar).
- [ ] `ruff check .` sem erros.

## Notes

Contratos são a fronteira para a futura versão web (jobs por estágio) — manter campos simples
(listas, floats, strings), sem objetos torch/numpy nos contratos (converter antes).

Verificação (venv `.venv/`, Python 3.11.15):

- `.venv/bin/pytest -q tests/test_models.py tests/test_cache.py` → `16 passed in 0.02s`
- `.venv/bin/ruff check .` → `All checks passed!`
- `grep -rE "import typer|import rich|print\(" tabgen/core/` → sem saída, exit 1 (core puro)

Desenho: dataclasses `SeparationResult`, `AnalysisResult`, `Note`, `NoteEvents`, `TabScore`
(esqueleto) com mixin `to_dict`/`to_json`/`from_dict`/`from_json`; só builtins nos campos —
`test_to_dict_is_json_dumpable_without_custom_encoder` cobre as cinco com `json.dumps` padrão.
Cache: `StageCache(input_path)`, dir `.tabgen/` ao lado do áudio, entrada
`{stage}-{sha256}-{version}.json`; versão no nome ⇒ bump de versão é miss natural; JSON corrompido
tratado como miss. `pipeline.py`: `ProgressCallback = Callable[[str, float], None]` + `null_progress`.

## Execution Log

- **Closed** — commit `db3c462` (2026-10-26): feat(core): add stage contract dataclasses, disk cache, and progress callback
  - Files (`git show --name-status db3c462`):
    - `A tabgen/core/cache.py`
    - `A tabgen/core/models.py`
    - `A tabgen/core/pipeline.py`
    - `A tests/test_cache.py`
    - `A tests/test_models.py`
- **Reviewed** (2026-10-26) at `72e2dd0`: FIX-FMVP-001
