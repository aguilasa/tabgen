---
id: TAB-TASK-03
---

# TAB-TASK-03 — Atribuir corda e casa por programação dinâmica

## Goal

Existe `tabgen/core/fretting/`: dado `NoteEvents` (e opcionalmente os acordes do
`AnalysisResult`), atribui a cada nota uma (corda, casa) por programação dinâmica — estado =
posição da mão; custo = deslocamento + abertura de dedos + penalidade de corda solta fora de
contexto + bônus por forma do acorde vigente — com afinação, nº de cordas, capo e casa máxima
configuráveis. Notas fora da tessitura são relatadas, não descartadas em silêncio.

## Escopo

- In: candidatos (corda, casa) por pitch; agrupamento de notas simultâneas (acorde = uma corda por
  nota); DP/Viterbi sobre a sequência; prior de acordes do estágio 2; presets guitarra 6 / baixo 4;
  testes com escalas e acordes conhecidos. Ler tuttut/tayuya como referência, sem dependência.
- Out: ML (TabCNN/TART); técnicas; afinações exóticas além de configurar `tuning_midi` (Fase 4).

## Done criteria

- [x] Teste: escala de Lá menor pentatônica na 5ª casa (pitches 57,60,62,64,67,69,72,74,76,79,81)
      sai toda entre as casas 5 e 8 (box position), sem saltos >4 casas entre notas vizinhas.
- [x] Teste: notas simultâneas nunca compartilham corda; tríade de Dó maior aberta
      (48,52,55,60,64) com acorde `C:maj` vigente sai na forma aberta (casas 3,2,0,1,0).
- [x] Teste: afinação drop D (`[38,45,50,55,59,64]`) coloca o pitch 38 na corda 6 casa 0; pitch
      fora da tessitura aparece na lista de não atribuídas.
- [x] Teste: baixo 4 cordas (`[28,33,38,43]`) atribui todas as notas de uma linha em E menor.
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Coração do valor próprio do projeto (plano, Estágio 5). Custo e pesos ficam como parâmetros
nomeados para ajuste na Fase 4; registrar nas Notes os pesos escolhidos e por quê.

Implementado em `tabgen/core/fretting/dp.py` (API pública re-exportada em
`tabgen/core/fretting/__init__.py`): Viterbi sobre *frames* de notas simultâneas
(onsets dentro de 30 ms); estado = (colocação do frame, posição da mão), onde a posição é uma
janela de `position_span` casas (indicador na posição, mínimo na posição+span−1); frame todo em
cordas soltas herda a posição anterior. Notas fora da tessitura vão para
`FrettingResult.unassigned` com motivo, nunca descartadas nem exceção.

Pesos escolhidos (defaults de `FrettingConfig`) e porquê:

- `displacement_weight = 1.0` — unidade de referência: 1 ponto por casa de deslocamento da mão
  entre frames; é o custo dominante, o que mantém linhas melódicas numa mesma box.
- `stretch_weight = 0.7` — abertura de dedos dentro de um frame (casa máx − mín entre notas
  presas); um pouco mais barato que mover a mão, para acordes compactos vencerem sem proibir
  aberturas.
- `open_string_penalty = 2.0` — por nota solta "fora de contexto" (não endossada pela forma do
  acorde vigente); alto o bastante para a pentatônica não escorregar para cordas soltas, mas
  anulado quando a solta pertence à forma do acorde.
- `chord_shape_bonus = 3.0` — bônus por nota que casa com a forma canônica do acorde vigente
  (tabela `CHORD_SHAPES`, maj/min comuns em afinação padrão); com 5 notas casando (−15) domina
  qualquer voicing alternativo, garantindo a forma aberta de C:maj.
- `high_fret_weight = 0.05` — custo suave por número da casa; desempata em favor de posições
  mais baixas sem sobrepujar os termos físicos.
- `string_index_weight = 0.4` — preferência suave por cordas mais graves; desambigua entre
  boxes equivalentes da pentatônica, escolhendo a box convencional da posição da tônica
  (5ª casa) em vez da box equivalente nas casas 2–5 (com `high_fret_weight` 0.05, a diferença
  0.4×5 = 2.0 supera 0.05×24 = 1.2 em favor da box da 5ª posição).

Decisões registradas:

- A lista de pitches do critério 1 (57…81) está em *written pitch* (violão/guitarra é
  instrumento transpositor, escrito uma oitava acima do som real): com a afinação padrão
  soante `[40,45,50,55,59,64]`, os pitches 74–81 só existem acima da casa 8. O teste usa a
  afinação escrita `[52,57,62,67,71,76]` (parâmetro `tuning_midi`, que é configurável por
  design) e o box 5–8 sai exato.
- Numeração de cordas no resultado segue a convenção de guitarrista do critério 3 (corda 6 =
  mais grave, corda 1 = mais aguda), ou seja `string = n_cordas − índice_low_to_high`.
  Atenção: o docstring de `TabNote` em `models.py` diz o oposto ("string 1 = lowest-pitched");
  conflito encaminhado para reconciliação na revisão/TASK-05 (não editei `models.py`).
- Frame com mais notas que cordas (ou sem colocação completa possível): fallback guloso coloca
  o que couber e relata o resto em `unassigned` com motivo "no free string".

Verificação (comandos e saída decisiva):

- Critérios 1–4: `.venv/bin/pytest -q tests/test_fretting.py` → `7 passed`.
  Pentatônica atribuída (pitch, corda, casa): `(57,6,5) (60,6,8) (62,5,5) (64,5,7) (67,4,5)
  (69,4,7) (72,3,5) (74,3,7) (76,2,5) (79,2,8) (81,1,5)` — box 5–8 clássica, salto máx 3.
  C:maj → `{48:(5,3), 52:(4,2), 55:(3,0), 60:(2,1), 64:(1,0)}`; drop D → `(38,6,0)` e pitch 30
  em `unassigned`; baixo 4 cordas → 9/9 notas atribuídas.
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1).
- `.venv/bin/ruff check .` → `All checks passed!`; `.venv/bin/pytest -q` → suíte toda verde,
  0 falhas.

## Execution Log

- **Closed** — commit `a9012b3` (2026-10-27): feat(fretting): assign string/fret via hand-position Viterbi with chord priors
  - Files (`git show --name-status a9012b3`):
    - `M docs/rite/cycles/tablatura/03-atribuir-corda-e-casa-por-programacao-dinamica.md`
    - `M tabgen/core/fretting/__init__.py`
    - `A tabgen/core/fretting/dp.py`
    - `A tests/test_fretting.py`
