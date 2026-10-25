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

## Execution Log
