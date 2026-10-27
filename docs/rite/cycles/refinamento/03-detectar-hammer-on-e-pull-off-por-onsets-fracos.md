---
id: REF-TASK-03
---

# REF-TASK-03 — Detectar hammer-on e pull-off por onsets fracos

## Goal

Existe heurística de legato: uma nota cujo ataque é fraco (velocity/amplitude bem abaixo da
nota anterior), que começa logo ao fim da anterior e fica na mesma corda vira hammer-on (pitch
sobe) ou pull-off (pitch desce), preenchendo a técnica da `TabNote` (plano, Fase 4).

## Escopo

- In: critérios nomeados (razão de amplitude, gap máximo, mesma corda, intervalo ≤ 5 casas);
  aplicada depois do fretting; testes sintéticos.
- Out: tapping, trinados como técnica própria; classificador de ML.

## Done criteria

- [x] Teste: casa 5 forte seguida de casa 7 com amplitude 30% e gap 0 na mesma corda vira
      hammer-on; 7 → 5 nas mesmas condições vira pull-off.
- [x] Teste: mesma sequência com segunda nota forte, com gap > limiar ou em outra corda não vira
      legato.
- [x] Teste: primeira nota de um compasso após pausa nunca é marcada como legato.
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Heurística sem ground truth local; a qualidade real é medida pelo harness (TASK-06) se o dataset
tiver anotação de técnica (EGDB/Guitar-TECHS) — registrar se não tiver.

### Áudio de teste (YouTube)

Pode baixar áudio de músicas conhecidas no YouTube com `yt-dlp` (instalado, 2026.08.19)
para conferir a detecção em gravação real.

Candidatas com hammer-on e pull-off claros:

- AC/DC — "Back in Black" (riff principal: hammer-ons e pull-offs na corda solta).
- Jimi Hendrix — "Little Wing" (intro: hammer-ons em formas de acorde).
- Led Zeppelin — "Stairway to Heaven" (solo: sequências de pull-off).

O áudio fica fora do repositório (`out/` ou scratchpad, ambos ignorados; nunca versionar), é
usado só para conferência e não vira número de done criterion: pela regra do `CLAUDE.md`, arquivo
baixado não é evidência reproduzível — os critérios continuam nos testes e probes sintéticos.
Baixar só o trecho necessário (`--download-sections`) quando possível. Se o `yt-dlp` falhar ou o
vídeo não existir, trocar por outra música da lista e registrar nas Notes.

```sh
yt-dlp -x --audio-format mp3 -o 'out/audio/%(title)s.%(ext)s' "ytsearch1:<artista> <música>"
yt-dlp -x --audio-format mp3 --download-sections '*<mm:ss>-<mm:ss>' -o 'out/audio/%(title)s.%(ext)s' "ytsearch1:<artista> <música>"
```

Encaminhado pela REF-TASK-01 (2026-10-27): contrato pronto — `Note.bends` (bins de 1/3 de semitom
relativos a `pitch_midi`, um por frame; `None` sem dados) e `TabNote.technique: Technique | None`
(`kind` em `TECHNIQUE_KINDS`; `bend_semitones`, `bend_curve`, `slide_direction` `SLIDE_UP`/`SLIDE_DOWN`,
`target_fret`). Convenção no docstring de `Technique`: a técnica fica na nota de ORIGEM; slide,
hammer-on e pull-off ligam à próxima nota na mesma corda e `target_fret` é o traste dela. Hoje
fretting/pipeline não copiam técnicas: toda `TabNote` sai com `technique=None`.

### Implementação (REF-TASK-03)

`tabgen/core/techniques/legato.py`: `detect_legato(events, notes, config=None)` com a mesma forma
da API de bends (REF-TASK-02): `notes[i]` é a nota transcrita de `events[i]`; função pura (cópias
via `dataclasses.replace`), `ValueError` se os comprimentos diferem, nunca sobrescreve técnica
existente. A técnica vai na nota de ORIGEM (`hammer_on`/`pull_off`, `target_fret` = casa do alvo).

Definições (também no docstring do módulo):

- Origem = última nota na MESMA corda que começa antes do alvo; notas em outras cordas no meio
  não importam (permite 5h7p5 com corda solta soando em outra corda).
- Contíguo: `-max_overlap_s <= alvo.start_s - origem.end_s <= max_gap_s`. Gap acima de
  `max_gap_s` é pausa naquela corda: o alvo é reatacado e nunca vira legato. Por isso a primeira
  nota de um compasso após pausa nunca é marcada — a regra não precisa olhar compasso.
- Direção pela casa: casa do alvo maior = hammer-on; menor = pull-off.

Limiares (`LegatoConfig`) e porquê:

- `max_amplitude_ratio = 0.6`: no legato a nota alvo não recebe palhetada e sai bem mais fraca;
  0.6 separa com folga o caso de teste (30%) de reataques com dinâmica parecida (≈ 0.8–1.0) e
  tolera hammer-ons fortes (que costumam ficar em 40–60% do ataque). Sem ground truth local; ajuste
  fica para o harness.
- `max_gap_s = 0.035`: ≈ 3 frames do Basic Pitch (~86 fps); legato real é contíguo e o offset da
  origem costuma ser cortado alguns frames antes do onset seguinte.
- `max_overlap_s = 0.05`: o transcritor às vezes deixa a origem soando um pouco além do onset do
  alvo; sobreposição maior que isso indica notas simultâneas, não sucessão.
- `max_fret_interval = 5`: alcance de dedo de uma mão parada (escopo do item); mesma casa (0) é
  nota repetida, não legato.

Controle antes do teste: com o critério de amplitude desligado (regra ingênua; linha trocada por
`if False:` temporariamente e restaurada), `pytest -q tests/test_techniques_legato.py` deu
`FAILED tests/test_techniques_legato.py::test_strong_second_note_is_not_legato` (e
`test_config_ratio_is_honored`), `2 failed, 14 passed`. Com a regra completa: `16 passed`.

Verificação:

- `.venv/bin/pytest -q tests/test_techniques_legato.py` → `16 passed` (hammer-on/pull-off,
  segunda nota forte, gap acima do limiar, outra corda, primeira nota do compasso após pausa,
  intervalo > 5, mesma casa, sobreposição pequena, cadeia 5h7p5, ordem, não-mutação).
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → sem saída (exit 1).
- `.venv/bin/pytest -q` → verde; `.venv/bin/ruff check tabgen/core/techniques/legato.py
  tests/test_techniques_legato.py` → `All checks passed!` (o `ruff check .` da árvore depende
  também dos arquivos da REF-TASK-02, editados em paralelo).

Ainda não ligado ao pipeline/export: o encadeamento depois do fretting (com bends/slides) é da
REF-TASK-04.

Anotação de técnica nos datasets: não verificada aqui (sem download). Pelo que se sabe dos papers,
EGDB traz só anotação de notas (MIDI por corda), sem técnica; Guitar-TECHS organiza gravações por
técnica (inclui legato), o que daria rótulo ao menos por arquivo. Confirmar e medir na REF-TASK-06.
Áudio real do YouTube não foi baixado (opcional).

Verificação (2026-10-27, thread principal, árvore do commit, sobre a REF-TASK-02 já commitada):

- `.venv/bin/pytest -q tests/test_techniques_legato.py` → `16 passed in 0.02s`
- `.venv/bin/pytest -q` → `168 passed, 11 warnings`; `.venv/bin/ruff check .` → `All checks passed!`
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1)
- Controle (worker): sem o critério de amplitude, `2 failed, 14 passed`
  (`test_strong_second_note_is_not_legato`, `test_config_ratio_is_honored`); restaurado, `16 passed`.
- Anotação de técnica nos datasets não conferida aqui (sem download); encaminhado à REF-TASK-06.

## Execution Log

- **Closed** — commit `6c21279` (2026-10-27): feat(core): detect hammer-on and pull-off from weak legato onsets
  - Files (`git show --name-status 6c21279`):
    - `M docs/rite/cycles/refinamento/03-detectar-hammer-on-e-pull-off-por-onsets-fracos.md`
    - `M docs/rite/cycles/refinamento/06-criar-harness-de-avaliacao-em-guitarset-e-egdb.md`
    - `A tabgen/core/techniques/legato.py`
    - `A tests/test_techniques_legato.py`
  - **Files amended** — added to `files`:
    - `docs/rite/cycles/refinamento/06-criar-harness-de-avaliacao-em-guitarset-e-egdb.md`
- **Reviewed** (2026-10-27) at `96adbf7`: no finding
