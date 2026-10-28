---
id: REF-TASK-07
---

# REF-TASK-07 — Avaliar modelo de transcrição específico de guitarra

## Goal

Há uma decisão registrada, com números do harness (TASK-06), sobre substituir o estágio 4 por
um modelo específico de guitarra (plano, Estágio 4: Riley et al. 2024; TART): verificar se código e
pesos estão públicos e com licença compatível; se sim, rodar no mesmo subset e comparar com o
Basic Pitch; entregar recomendação. A troca em si não faz parte (decisão do usuário).

## Escopo

- In: levantamento de disponibilidade e licença (Riley 2024, TART, YourMT3+ como controle);
  wrapper experimental fora do core (`scripts/eval/`) para o candidato disponível; comparação no
  subset do harness; documento de decisão em `docs/`.
- Out: integrar o modelo ao `core`/CLI (tarefa nova se a recomendação for trocar).

## Done criteria

- [x] Documento `docs/avaliacao/modelo-guitarra.md` existe com: links e licenças verificados, tabela
      nota-F1/tab-F1 de Basic Pitch vs candidato(s) no mesmo subset, comando que gera cada número e
      recomendação.
- [x] Se nenhum candidato tiver código/pesos públicos, o documento registra a verificação (URLs e
      data) e a recomendação é manter o Basic Pitch.
- [x] `.venv/bin/pytest -q` verde (o wrapper experimental não entra no core).

## Notes

Licença: modelos non-commercial são aceitos (plano, seção 4); AGPL evitada. Downloads de pesos
exigem confirmação do usuário.

Execução (2026-10-28):

- Disponibilidade: Riley 2024 tem pesos públicos em `huggingface.co/xavriley/midi-transcription-models`
  (MIT): `guitar-fl.pth` (artigo ICASSP 2024) e `guitar-gaps.pth` (GAPS, ISMIR 2024). TART sem código.
  YourMT3+ disponível (GPL-3.0, GuitarSet no treino), não rodado. Detalhes e URLs no documento.
- Download autorizado pelo usuário nesta sessão ("Baixar os dois pesos"): pesos em
  `~/datasets/tabgen/candidates/weights/` (sha256 `50d93dba89bd…`, `65483e7c0e34…`, iguais aos OIDs do
  HF); inferência (`xavriley/piano_transcription_inference` + `torchlibrosa`) com
  `pip install --no-deps --target ~/datasets/tabgen/candidates/site`, fora do `.venv` e do repo.
- Critério 1: `.venv/bin/python scripts/eval/candidates.py --candidate <c> --dataset <d> --subset
  scripts/eval/subsets/<d>.txt` para c em basic-pitch, riley-fl, riley-gaps e d em guitarset, egdb:
  `basic-pitch guitarset: note-F1 0.761 tab-F1 0.341`, `basic-pitch egdb: note-F1 0.765 tab-F1 0.418`,
  `riley-fl guitarset: note-F1 0.925 tab-F1 0.468`, `riley-fl egdb: note-F1 0.843 tab-F1 0.429`,
  `riley-gaps guitarset: note-F1 0.892 tab-F1 0.453`, `riley-gaps egdb: note-F1 0.860 tab-F1 0.486`.
  Recomendação no documento: adotar Riley (`guitar-gaps`) em tarefa nova, condicionada a medir em
  stems do Demucs, manter bends do Basic Pitch e resolver a licença do código de inferência.
- Critério 2: não se aplica como caso negativo (há candidato público); a verificação com URLs e data
  está no documento.
- Critério 3: `.venv/bin/pytest -q` → `213 passed`; `ruff check .` → `All checks passed!`; grep de
  pureza em `tabgen/core/` vazio; `git status --porcelain tabgen tests` vazio (nada no core).
- Arquivos fora da lista: relatórios em `scripts/eval/reports/candidates/` (evidência versionada dos
  números, formato do `run.py`; os relatórios principais ficam com a REF-TASK-08).

## Execution Log

- **Closed** — commit `f8fb4d6` (2026-10-28): docs(eval): evaluate guitar-specific transcription models against Basic Pitch
  - Files (`git show --name-status f8fb4d6`):
    - `A docs/avaliacao/modelo-guitarra.md`
    - `M docs/rite/cycles/refinamento/07-avaliar-modelo-de-transcricao-especifico-de.md`
    - `M docs/rite/cycles/refinamento/08-fechar-fase-4.md`
    - `A scripts/eval/candidates.py`
    - `A scripts/eval/reports/candidates/basic-pitch/egdb-egdb.json`
    - `A scripts/eval/reports/candidates/basic-pitch/egdb-egdb.md`
    - `A scripts/eval/reports/candidates/basic-pitch/guitarset-guitarset.json`
    - `A scripts/eval/reports/candidates/basic-pitch/guitarset-guitarset.md`
    - `A scripts/eval/reports/candidates/riley-fl/egdb-egdb.json`
    - `A scripts/eval/reports/candidates/riley-fl/egdb-egdb.md`
    - `A scripts/eval/reports/candidates/riley-fl/guitarset-guitarset.json`
    - `A scripts/eval/reports/candidates/riley-fl/guitarset-guitarset.md`
    - `A scripts/eval/reports/candidates/riley-gaps/egdb-egdb.json`
    - `A scripts/eval/reports/candidates/riley-gaps/egdb-egdb.md`
    - `A scripts/eval/reports/candidates/riley-gaps/guitarset-guitarset.json`
    - `A scripts/eval/reports/candidates/riley-gaps/guitarset-guitarset.md`
  - **Files amended** — added to `files`:
    - `docs/rite/cycles/refinamento/08-fechar-fase-4.md`
    - `scripts/eval/reports/candidates/basic-pitch/egdb-egdb.json`
    - `scripts/eval/reports/candidates/basic-pitch/egdb-egdb.md`
    - `scripts/eval/reports/candidates/basic-pitch/guitarset-guitarset.json`
    - `scripts/eval/reports/candidates/basic-pitch/guitarset-guitarset.md`
    - `scripts/eval/reports/candidates/riley-fl/egdb-egdb.json`
    - `scripts/eval/reports/candidates/riley-fl/egdb-egdb.md`
    - `scripts/eval/reports/candidates/riley-fl/guitarset-guitarset.json`
    - `scripts/eval/reports/candidates/riley-fl/guitarset-guitarset.md`
    - `scripts/eval/reports/candidates/riley-gaps/egdb-egdb.json`
    - `scripts/eval/reports/candidates/riley-gaps/egdb-egdb.md`
    - `scripts/eval/reports/candidates/riley-gaps/guitarset-guitarset.json`
    - `scripts/eval/reports/candidates/riley-gaps/guitarset-guitarset.md`
- **Reviewed** (2026-10-28) at `25bb518`: no finding
