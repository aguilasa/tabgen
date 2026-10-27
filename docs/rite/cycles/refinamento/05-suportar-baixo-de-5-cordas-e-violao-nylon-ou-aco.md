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

- [ ] Teste: linha de baixo com B0 (pitch 23) é atribuída na corda 5 casa 0 com o preset de 5
      cordas; com o de 4 cordas aparece como não atribuída.
- [ ] Teste: .gp5 relido tem faixa de baixo com 5 cordas e afinação correta.
- [ ] Teste: `--guitar-type nylon` gera faixa com programa GM 24 no .gp5 e no MIDI.
- [ ] Teste: ASCII de baixo de 5 cordas tem 5 linhas por sistema.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

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

## Execution Log
