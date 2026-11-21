---
id: STEM-TASK-01
---

# STEM-TASK-01 — Separação preparada a partir de stems dados no core

## Goal

O core aceita stems já separados (por exemplo, do Moises). Ao receber `user_stems={"guitar": path}`,
`run_analysis`, `run_transcription` e `run_tablature` usam esses arquivos. O Demucs só é chamado
quando algum instrumento pedido fica sem stem; nesse caso os stems dados substituem os do Demucs. A
identidade dos stems dados entra nas versões de cache.

## Escopo

- In:
  - Novo `tabgen/core/separation/prepared.py`:
    - `prepared_separate(user_stems, fallback=None)` devolve um `_SeparateFn` com
      `SeparationResult(stems=..., model_version="user-stems:<hash>")`.
    - O `<hash>` é o sha256 de (instrumento, sha256 do arquivo), ordenado.
    - Se faltar instrumento, chama `fallback` (o Demucs) e sobrepõe os stems dados.
  - Parâmetro `user_stems: Mapping[str, str|Path] | None = None` em `run_analysis`,
    `run_transcription` e `run_tablature`. Quando ele vem, a função monta o `separate_fn` preparado.
    Um `separate_fn` injetado continua tendo prioridade nos testes.
  - Análise:
    - Os beats ficam no `input_path`.
    - A harmonia recebe os stems dados e mais `{"mix": input_path}` quando o input não for um deles.
    - `analysis_version()` ganha o sufixo do hash só quando há `user_stems`.
  - `transcription` e `tablature_version`: incluem o hash dos stems só quando há `user_stems`.
  - Validação: instrumento fora de `TABLATURE_INSTRUMENTS` ou arquivo inexistente levantam
    `PipelineError` com mensagem clara.
- Out:
  - CLI, worker e desktop (a CLI é a STEM-TASK-02).

## Done criteria

- [x] `.venv/bin/pytest -q tests/test_prepared_stems.py` passa. Os testes usam fakes (sem GPU) e
      cobrem:
  - `run_tablature(..., user_stems={"guitar": g}, instruments=("guitar",))` não chama o `separate`
    real do Demucs: um fake levanta erro se for chamado.
  - Caso parcial (`guitar` dado, `bass` pedido): o fallback é chamado uma vez e o stem `guitar` usado
    é o dado.
  - Duas execuções com stems de conteúdo diferente geram chaves de cache `tablature` diferentes.
  - Sem `user_stems`, `analysis_version()` e `tablature_version(...)` dão o mesmo valor do HEAD
    anterior. O valor esperado fica fixado no teste.
  - Stem inexistente ou instrumento `drums` → `PipelineError`.
- [x] `make test` passa (suíte inteira).
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` vazio.

## Notes

Ponto de injeção: `separate_fn` em `tabgen/core/pipeline.py` (`run_analysis` ~l.335,
`_compute_tablature` ~l.950). Contrato: `SeparationResult` em `tabgen/core/models.py:38`.

Evidência (2026-11-21):
- `.venv/bin/pytest -q tests/test_prepared_stems.py` → `10 passed`. Controle: com `tabgen/core/pipeline.py`
  do HEAD (`git stash push tabgen/core/pipeline.py`) → `7 failed, 3 passed`. Os 3 que passam testam só
  `prepared.py`.
- `make test` → `270 passed`; `ruff check .` → `All checks passed!`; o grep do core sai vazio (exit 1).
- Valores fixados de `analysis_version()` e `tablature_version()` sem stems: medidos num worktree do
  HEAD `3d5afb2` e no working tree, e são idênticos.
- Desvio do plano (decisão 5, "versões passam a incluir"): com stems, a tag `stems-<sha10>` **substitui**
  `htdemucs_ft+htdemucs_6s` em `analysis_version`, em vez de ser acrescentada. Motivo: o nome do arquivo
  de cache `tablature` já tem 253 bytes, a 2 do limite de 255 (`ls out/audio/.tabgen`). Quando o Demucs
  ainda roda (caso parcial), a versão dele entra no digest da tag. O teste confere `len(nome) <= 255`.

## Execution Log

- **Closed** — commit `e159ef3` (2026-11-21): feat(core): accept user-provided stems and skip Demucs when they cover every instrument
  - Files (`git show --name-status e159ef3`):
    - `M docs/rite/cycles/entrada-stems/01-separacao-preparada-a-partir-de-stems-dados-no.md`
    - `M tabgen/core/pipeline.py`
    - `A tabgen/core/separation/prepared.py`
    - `A tests/test_prepared_stems.py`
