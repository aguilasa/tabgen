---
id: REF-TASK-05
---

# REF-TASK-05 — Suportar baixo de 5 cordas e violão nylon ou aço

## Goal

O `tabgen export` suporta baixo de 5 cordas (preset `B0 E1 A1 D2 G2`, fretting e .gp5 com 5
cordas) e escolha do violão: `--guitar-type electric|nylon|steel` define o programa GM da faixa
(.gp5/MIDI/MusicXML) e limites de fretting próprios (casa máxima do violão nylon menor).

## Escopo

- In: preset `five-string` em `--bass-tuning`; `FrettingConfig` por tipo de instrumento; programa
  GM 24 (nylon), 25 (aço), 27/29 (elétrica) mapeado nos exportadores; ASCII com 5 linhas no baixo.
- Out: afinações exóticas além de notas explícitas (já suportadas por `--tuning`); 7 cordas.

## Done criteria

- [x] Teste: linha de baixo com B0 (pitch 23) é atribuída na corda 5 casa 0 com o preset de 5
      cordas; com o de 4 cordas aparece como não atribuída.
- [x] Teste: .gp5 relido tem faixa de baixo com 5 cordas e afinação correta.
- [x] Teste: `--guitar-type nylon` gera faixa com programa GM 24 no .gp5 e no MIDI.
- [x] Teste: ASCII de baixo de 5 cordas tem 5 linhas por sistema.
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Afinações alternativas e capo já existem (`--tuning`, `--bass-tuning`, `--capo`, Fase 3); esta
tarefa cobre só o que falta do item do plano.

### Áudio de teste (YouTube)

Pode baixar áudio de músicas conhecidas no YouTube com `yt-dlp` (instalado, 2026.08.19)
para conferir a detecção em gravação real.

Candidatas por elemento:

- Baixo de 5 cordas (corda B grave): Korn — "Freak on a Leash"; Korn — "Blind".
- Violão nylon: Antônio Carlos Jobim / João Gilberto — "Garota de Ipanema"; "Romance Anónimo"
  (violão clássico solo); Isaac Albéniz — "Asturias" (violão).
- Violão de aço: Oasis — "Wonderwall"; The Beatles — "Blackbird"; Eric Clapton — "Tears in
  Heaven" (unplugged).

O áudio fica fora do repositório (`out/` ou scratchpad, ambos ignorados; nunca versionar), é
usado só para conferência e não vira número de done criterion: pela regra do `CLAUDE.md`, arquivo
baixado não é evidência reproduzível — os critérios continuam nos testes e probes sintéticos.
Baixar só o trecho necessário (`--download-sections`) quando possível. Se o `yt-dlp` falhar ou o
vídeo não existir, trocar por outra música da lista e registrar nas Notes.

```sh
yt-dlp -x --audio-format mp3 -o 'out/audio/%(title)s.%(ext)s' "ytsearch1:<artista> <música>"
yt-dlp -x --audio-format mp3 --download-sections '*<mm:ss>-<mm:ss>' -o 'out/audio/%(title)s.%(ext)s' "ytsearch1:<artista> <música>"
```

Encaminhado pela REF-TASK-04 (2026-10-28): esta task mexe nos mesmos exporters e na CLI. Preservar:
notas de segmento como triplas `(string, fret, technique)` em gp5 e musicxml; a flag `last` em
`_Segment`/`_append_beats` do gp5 (slide/hammer vão no último pedaço ligado); spanners ligados pela
ordem das cadeias no musicxml; a regra de largura de célula do ASCII (mantém
`tests/golden/ascii_guitar_riff.txt` idêntico); `run_tablature(techniques=...)`, a tag `+tech-...` na
versão de cache e a opção `--techniques/--no-techniques`.
Achado da REF-04 sobre `tabgen/core/fretting/dp.py` (arquivo desta task): com `FrettingConfig` padrão,
a linha esparsa D4, A4, B4, E4 (`Note(62,0.5,0.95)`, `Note(69,1.0,1.25)`, `Note(71,1.25,1.45)`,
`Note(64,2.0,2.45)`) sai em `(6,22), (5,24), (4,21), (6,24)` — casas 21–24 nas cordas graves, com ou
sem acordes. Os testes de técnica injetam fretting fixo por causa disso. Avaliar aqui ou abrir fix.

### Implementação (REF-TASK-05, 2026-10-28)

- Onde vive o tipo de violão: campo novo `TabScore.instrument_type` (contrato; `""` = tipo padrão
  do instrumento; payload antigo carrega `""`). `TAB_FORMAT_VERSION` 2 → 3 e
  `TABLATURE_PIPELINE_REVISION` 2 → 3. Constantes em `models.py`: `GUITAR_TYPES`
  (`electric`, `nylon`, `steel`), `DEFAULT_GUITAR_TYPE = "electric"`, `BASS_FIVE_STRING_TUNING`
  (`[23, 28, 33, 38, 43]`) e `gm_program(instrument, instrument_type)`, a tabela GM única usada
  por gp5, MIDI e MusicXML (antes duplicada em `midi.py` e `gp5.py`).
- Programa GM: nylon 24, aço 25, elétrica 27 (Electric Guitar clean — escolhido em vez de 29,
  overdriven, porque a transcrição não distingue distorção); baixo 33. Mudança de comportamento:
  o padrão do violão passa de 25 (aço) para 27 (elétrica) em gp5 e MIDI; MusicXML antes não
  escrevia `<midi-instrument>` e agora escreve (1-based: `<midi-program>25</midi-program>` = GM 24).
- Fretting por tipo: `GUITAR_MAX_FRETS` em `dp.py` — elétrica 24 (padrão antigo mantido), aço 20,
  nylon 19; `guitar_config(guitar_type)` aplica, `five_string_bass_config()` é o preset do baixo
  de 5 cordas. Preset `five-string` em `TUNING_PRESETS["bass"]` (cobre também o FIX-REF-003).
- Pipeline e CLI: `run_tablature(guitar_type=...)` leva o tipo ao `FrettingConfig` do violão e ao
  `TabScore`; `run_transcription(guitar_type=...)` passa `instrument_type` ao exportador MIDI só do
  violão (sem tipo, o exportador recebe exatamente os mesmos argumentos de antes).
  `tabgen export --guitar-type electric|nylon|steel` (padrão `electric`; inválido sai com código
  2) e `tabgen transcribe --guitar-type`. O resumo da CLI mostra o tipo só quando não é o padrão.
- Cache: o digest de `FrettingConfig` já cobria afinação (portanto o número de cordas do preset
  de 5 cordas), capo e `max_fret`; foi adicionada a tag `+gtype-<tipo>` porque aço/nylon podem
  divergir só no programa GM, que vai no payload cacheado.
- ASCII e gp5 já aceitavam N cordas antes desta task (conferido no HEAD com afinação de 5 cordas:
  5 linhas por sistema e faixa .gp5 com 5 cordas); o que faltava era preset, fretting e tipo.
  `ascii_tab.py` não foi alterado; os goldens seguem idênticos.
- Controle: os testes novos rodados contra um snapshot do HEAD falham (import de
  `five_string_bass_config`/`BASS_FIVE_STRING_TUNING`, `TabScore(instrument_type=...)` e
  `export_midi(instrument_type=...)` inexistentes; o teste de regressão do fretting falha com
  `AssertionError: [22, 24, 21, 24]`).

### Achado da REF-04 sobre o fretting (corrigido aqui)

Reproduzido: a linha D4 A4 B4 E4 saía em `(6,22), (5,24), (4,21), (6,24)`. Causa raiz: no custo por
nota, subir uma corda economiza 5 casas × `high_fret_weight` 0,05 = 0,25, mas custa
`string_index_weight` 0,4; logo a corda mais grave que alcança a nota (a casa mais alta) sempre
vence, e o Viterbi não corrige porque ficar no alto não gera deslocamento. Correção pequena:
`comfort_max_fret = 12` e `above_comfort_weight = 0,5` por casa acima da 12ª em `FrettingConfig`
(pesos antigos intactos, então caixa pentatônica 5–8, C aberto, drop-D e baixo seguem verdes).
Depois: `(4,12), (2,10), (2,12), (3,9)` sem acordes e `(4,12), (2,10), (2,12), (1,0)` com E:min.
O viés para cordas graves continua dentro das casas 0–12 (é ele que mantém a caixa pentatônica);
uma posição mais natural (ex.: casa 7) pediria rebalancear pesos com o harness de avaliação.
Teste de regressão: `test_sparse_line_is_not_pushed_above_the_twelfth_fret`.

Verificação (2026-10-28, thread principal, árvore do commit):

- Testes dos critérios (`test_five_string_bass_places_low_b_open_on_string_five`,
  `test_five_string_bass_track_keeps_five_strings_and_tuning`,
  `test_five_string_bass_preset_and_guitar_type_reach_the_gp5`, `test_guitar_type_sets_the_track_program`,
  `test_instrument_type_sets_the_gm_program`, `test_run_transcription_guitar_type_reaches_the_midi_file`,
  `test_cli_guitar_type_and_five_string_bass`, `test_guitar_type_sets_the_part_midi_program`,
  `test_five_string_bass_has_five_string_lines_per_system`, `test_sparse_line_is_not_pushed_above_the_twelfth_fret`)
  → `.venv/bin/pytest -q <esses 10 + 6 do worker>` → `16 passed`
- `.venv/bin/pytest -q` → `213 passed`; `.venv/bin/ruff check .` → `All checks passed!`;
  `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1);
  `git diff --quiet -- tests/golden/` → exit 0 (goldens intactos)
- Controle (worker): os testes novos contra `git archive HEAD` → 14 falhas (ex.:
  `AssertionError: [22, 24, 21, 24]` no teste da linha esparsa).
- Efeito do novo custo acima da casa 12 na avaliação (REF-TASK-06), relatório no scratchpad, sem
  alterar os versionados: `.venv/bin/python scripts/eval/run.py --dataset guitarset --subset
  scripts/eval/subsets/guitarset.txt --out <scratch>` → `mean note-F1 0.761, mean tab-F1 0.341`
  (antes 0.313); `--dataset egdb` → `mean note-F1 0.765, mean tab-F1 0.418` (antes 0.383).
- Fora da lista declarada e justificado: `tabgen/core/pipeline.py` (tipo e preset passam por
  `run_tablature`/`run_transcription`; versão de cache), `tests/test_tablature_pipeline.py`,
  `tests/test_midi_export.py`, `tests/test_musicxml_export.py`. Declarado e não tocado:
  `tabgen/core/export/ascii_tab.py` (já renderizava N cordas).

## Execution Log

- **Closed** — commit `1814053` (2026-10-28): feat(export): support 5-string bass preset and guitar type (electric/nylon/steel)
  - Files (`git show --name-status 1814053`):
    - `M docs/rite/cycles/refinamento/05-suportar-baixo-de-5-cordas-e-violao-nylon-ou-aco.md`
    - `M docs/rite/cycles/refinamento/08-fechar-fase-4.md`
    - `M docs/rite/cycles/refinamento/FIX-REF-003.md`
    - `M tabgen/cli/main.py`
    - `M tabgen/core/export/gp5.py`
    - `M tabgen/core/export/midi.py`
    - `M tabgen/core/export/musicxml.py`
    - `M tabgen/core/fretting/dp.py`
    - `M tabgen/core/models.py`
    - `M tabgen/core/pipeline.py`
    - `M tests/test_ascii_tab.py`
    - `M tests/test_fretting.py`
    - `M tests/test_gp5_export.py`
    - `M tests/test_midi_export.py`
    - `M tests/test_musicxml_export.py`
    - `M tests/test_tablature_pipeline.py`
  - **Files amended** — added to `files`:
    - `docs/rite/cycles/refinamento/08-fechar-fase-4.md`
    - `docs/rite/cycles/refinamento/FIX-REF-003.md`
    - `tabgen/core/pipeline.py`
    - `tests/test_midi_export.py`
    - `tests/test_musicxml_export.py`
    - `tests/test_tablature_pipeline.py`
