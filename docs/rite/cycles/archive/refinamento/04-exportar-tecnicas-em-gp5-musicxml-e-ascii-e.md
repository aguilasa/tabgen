---
id: REF-TASK-04
---

# REF-TASK-04 — Exportar técnicas em gp5, MusicXML e ASCII e ligar no pipeline

## Goal

As técnicas saem nos formatos: .gp5 grava bend (`BendEffect`), slide e hammer-on/pull-off
(`NoteEffect`) via PyGuitarPro; MusicXML grava as notações equivalentes (`bend`, `slide`/`glissando`,
`hammer-on`/`pull-off`); a tab ASCII usa as marcas usuais (`7b9`, `5/7`, `7\5`, `5h7`, `7p5`).
`run_tablature` aplica as detecções (TASK-02/03) e `tabgen export` passa a gerá-las, com flag
para desligar (`--no-techniques`).

## Escopo

- In: mapeamento técnica → efeito em cada exportador; ligação no pipeline após fretting; versão
  de cache do estágio de tablatura incluindo o conjunto de técnicas; golden ASCII novo; atualizar
  `scripts/probe_e2e_export.py` só com fatos estáveis.
- Out: técnicas além das da TASK-01.

## Done criteria

- [x] Teste: `TabScore` com as quatro técnicas exportada em .gp5 e relida com `guitarpro.parse()`
      preserva cada efeito na nota correta.
- [x] Teste: MusicXML relido pelo music21 contém as notações técnicas nas notas correspondentes.
- [x] Teste: golden ASCII versionado em `tests/golden/` com bend, slide, hammer e pull bate byte a
      byte.
- [x] `--no-techniques` gera saída sem nenhum efeito (teste de CLI com funções injetadas).
- [x] `.venv/bin/python scripts/probe_e2e_export.py` sai 0.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Hot files: `tabgen/core/pipeline.py`, `tabgen/cli/main.py`, `tabgen/core/export/*`. Regra do
`CLAUDE.md`: conferir `files` contra o diff antes do `rite finish`.

### Áudio de teste (YouTube)

Pode baixar áudio de músicas conhecidas no YouTube com `yt-dlp` (instalado, 2026.08.19)
para conferir a detecção em gravação real.

Para conferir no TuxGuitar que os efeitos exportados batem com o que se ouve, reutilizar o
áudio das TASK-02/03 (um trecho de "Comfortably Numb" para bend e "Back in Black" para legato).

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
Exportar a partir da nota de origem até a próxima na mesma corda (ASCII `5h7`, MusicXML
start/stop, flags de efeito GP5). Comentário desatualizado em `tabgen/core/export/midi.py:38` (diz
que os bends vêm de `TranscriptionResult.bends`; agora vêm de `Note.bends`) — corrigir aqui.

Encaminhado pelas REF-TASK-02/03 (2026-10-27): detectores com assinatura comum
`detect_bends_and_slides(events, notes, config=None)` (`tabgen/core/techniques/bends.py`, `BendConfig`) e
`detect_legato(events, notes, config=None)` (`tabgen/core/techniques/legato.py`, `LegatoConfig`): puros,
devolvem cópias, nunca sobrescrevem técnica existente — a ordem de chamada define a precedência
(sugerido: bends/slides, depois legato). `notes` precisa ser paralelo aos eventos do fretting, e o
fretting/pipeline hoje não guarda esse vínculo (o pipeline mapeia por `id(note)` em `_fretting_input`).
Exportar as legato no `__init__.py` de `tabgen/core/techniques/` (a REF-03 não podia editá-lo).
`bend_curve` sai com 5 pontos em passos de 0,5 semitom (mapear para pontos de bend GP5); slide e
legato com `target_fret` na nota de origem (ASCII `/`, `\`, `h`, `p`). Limitação conhecida: glide na
cauda de nota numa corda diferente da seguinte vira bend.

### Execução (REF-TASK-04)

- **Vínculo no pipeline:** `QuantizedNote` e as cópias de `_fretting_input` perdem `Note.bends`, mas
  o `QuantizedNote` guarda `pitch_midi`/`start_s`/`end_s` originais sem alteração; `_source_notes`
  mapeia cada par `(q, f)` de volta à `Note` transcrita por essa tripla (triplas iguais são a
  mesma nota para os detectores; sem correspondência, cópia sem bends). Escolhido em vez de mexer
  em `quantize.py` (fora da lista de arquivos). `_detect_techniques` chama
  `detect_bends_and_slides` e depois `detect_legato` (ordem = precedência).
- **Cache:** `tablature_version(configs, techniques=True)` termina em `+tech-off` ou
  `+tech-<sha12 de BendConfig+LegatoConfig>`; `TABLATURE_PIPELINE_REVISION` = 2.
  `run_tablature(..., techniques=True)`; CLI `tabgen export --techniques/--no-techniques`
  (padrão ligado; com técnicas, o resumo por instrumento mostra `N technique(s)`).
- **GP5:** bend → `BendEffect(type=bend, value=semitons*50)` na primeira batida da nota; pontos
  do `bend_curve` em posições 0..12 com valor em quartos de tom (unidade do PyGuitarPro:
  `semitoneLength=1` grava ×25 no arquivo); sem curva, sobe ao pico e segura. Slide →
  `SlideType.shiftSlideTo`; hammer-on e pull-off → `NoteEffect.hammer` (GP5 usa um só flag), os
  dois na última batida da nota (após ligaduras) para ligar à nota seguinte.
- **MusicXML:** bend → `<technical><bend><bend-alter>` (`FretBend`) no primeiro elemento; slide →
  `<slide line-type="solid">` (`Glissando` `continuous`); hammer/pull → spanners `HammerOn`/
  `PullOff` (start/stop) do último elemento da origem ao primeiro da próxima nota na mesma
  corda; técnica de ligação sem nota seguinte na corda é descartada.
- **ASCII:** marca na célula da origem: `7b9` (alvo = traste + semitons, `:g`; quarto de tom
  vira `7b8.5`), `5/`, `7\`, `5h`, `7p`. A largura da célula conta só trastes e tokens de bend
  (+1), então o golden antigo `ascii_guitar_riff.txt` fica idêntico; sem bend e com notas em
  células vizinhas sai `5h7p5`; com bend na mesma partitura (largura 4) sai `5h--7`.
- **Controle (antes do mapeamento):** com `_apply_technique`/`_link_spanner`/`_cell_token`
  anulados por monkeypatch (script em scratchpad, não versionado), os três testes de técnica
  falham: gp5 `At index 0 diff: (3, 7, None, [], False) != (3, 7, [(0, 0), (3, 2), (6, 4), (9, 4),
  (12, 4)], [], False)`; MusicXML `assert 'line-type="solid"' in ...`; ASCII `At index 154 diff:
  b'-' != b'h'` → `3 failed`.
- **Comandos dos critérios:**
  - gp5: `.venv/bin/pytest -q tests/test_gp5_export.py` → `7 passed`
    (`test_techniques_roundtrip_as_note_effects`).
  - MusicXML: `.venv/bin/pytest -q tests/test_musicxml_export.py` → `6 passed`
    (`test_techniques_reread_as_technical_notations`).
  - ASCII: `.venv/bin/pytest -q tests/test_ascii_tab.py` → `8 passed`
    (`test_golden_techniques_match_bytes`; `ascii_guitar_riff.txt` sem diff).
  - `--no-techniques`: `.venv/bin/pytest -q tests/test_tablature_pipeline.py` → `12 passed`
    (`test_cli_no_techniques_writes_no_effect`, CliRunner com estágios injetados e fretting
    fixo).
  - Probe: `.venv/bin/python scripts/probe_e2e_export.py` → exit 0, `PASS: ... --no-techniques
    gp5 has 0 note effects on its own cache entry (techniques on: 0 effect(s), not asserted).`
    O seno puro não gera técnica; a contagem com técnicas só é reportada.
  - `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes; grep de pureza em `tabgen/core/`
    vazio.
- **Não feito — comentário em `tabgen/core/export/midi.py:37-38`:** o comentário ainda diz que os
  bends vêm de `TranscriptionResult.bends` (agora vêm de `Note.bends`). A edição foi recusada pelo
  sistema de permissões nesta execução e fica para decisão do usuário; o arquivo não foi
  tocado.
- **Achado (encaminhar ao fretting):** `assign_frets` com a configuração padrão põe a linha
  esparsa D4, A4, B4, E4 (sem acordes) em `(6, 22), (5, 24), (4, 21), (6, 24)` — trastes 21–24
  nas cordas graves. Por isso o teste de pipeline das técnicas injeta um fretting fixo. Fora do
  escopo desta tarefa.
- Verificação opcional com áudio do YouTube: não feita (opcional).

Verificação (2026-10-28, thread principal, árvore do commit sem os arquivos da REF-TASK-06):

- `.venv/bin/pytest -q tests/test_gp5_export.py` → `7 passed`; `tests/test_musicxml_export.py` → `6 passed`;
  `tests/test_ascii_tab.py` → `8 passed`; `tests/test_tablature_pipeline.py` → `12 passed`
- `git diff --quiet -- tests/golden/ascii_guitar_riff.txt` → exit 0 (golden antigo intacto)
- `/usr/bin/time -f "elapsed=%es" .venv/bin/python scripts/probe_e2e_export.py` → exit 0, `PASS: ... cached
  rerun mentioned 'cache hit' in 0.24 s; --no-techniques gp5 has 0 note effects on its own cache entry`,
  `elapsed=14.97s`
- `.venv/bin/pytest -q` → `180 passed`; `.venv/bin/ruff check .` → `All checks passed!`;
  `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1)
- Controle (worker, script de scratchpad): mapeamentos trocados por no-op → `3 failed` nos três testes de
  técnica.

## Execution Log

- **Closed** — commit `c0a1f94` (2026-10-28): feat(export): write bends, slides and legato to gp5, MusicXML and ASCII
  - Files (`git show --name-status c0a1f94`):
    - `M docs/rite/cycles/refinamento/04-exportar-tecnicas-em-gp5-musicxml-e-ascii-e.md`
    - `M docs/rite/cycles/refinamento/05-suportar-baixo-de-5-cordas-e-violao-nylon-ou-aco.md`
    - `M docs/rite/cycles/refinamento/08-fechar-fase-4.md`
    - `M scripts/probe_e2e_export.py`
    - `M tabgen/cli/main.py`
    - `M tabgen/core/export/ascii_tab.py`
    - `M tabgen/core/export/gp5.py`
    - `M tabgen/core/export/musicxml.py`
    - `M tabgen/core/pipeline.py`
    - `M tabgen/core/techniques/__init__.py`
    - `A tests/golden/ascii_techniques.txt`
    - `M tests/test_ascii_tab.py`
    - `M tests/test_gp5_export.py`
    - `M tests/test_musicxml_export.py`
    - `M tests/test_tablature_pipeline.py`
  - **Files amended** — added to `files`:
    - `docs/rite/cycles/refinamento/05-suportar-baixo-de-5-cordas-e-violao-nylon-ou-aco.md`
    - `docs/rite/cycles/refinamento/08-fechar-fase-4.md`
    - `tabgen/core/techniques/__init__.py`
- **Reviewed** (2026-10-28) at `52ab18b`: FIX-REF-001
