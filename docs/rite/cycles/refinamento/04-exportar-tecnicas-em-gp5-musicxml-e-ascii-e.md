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

- [ ] Teste: `TabScore` com as quatro técnicas exportada em .gp5 e relida com `guitarpro.parse()`
      preserva cada efeito na nota correta.
- [ ] Teste: MusicXML relido pelo music21 contém as notações técnicas nas notas correspondentes.
- [ ] Teste: golden ASCII versionado em `tests/golden/` com bend, slide, hammer e pull bate byte a
      byte.
- [ ] `--no-techniques` gera saída sem nenhum efeito (teste de CLI com funções injetadas).
- [ ] `.venv/bin/python scripts/probe_e2e_export.py` sai 0.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

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

## Execution Log
