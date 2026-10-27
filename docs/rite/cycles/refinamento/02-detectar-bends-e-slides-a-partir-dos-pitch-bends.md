---
id: REF-TASK-02
---

# REF-TASK-02 — Detectar bends e slides a partir dos pitch bends

## Goal

Existe `tabgen/core/techniques/bends.py` (ou módulo equivalente em `core/`): a partir dos pitch
bends por nota, classifica bend (desvio sustentado ≥ ½ tom acima do pitch, com retorno opcional)
e slide (transição contínua entre duas notas consecutivas na mesma corda com glissando de pitch),
preenchendo a técnica da `TabNote`. Vibrato curto e ruído de pitch não viram bend.

## Escopo

- In: suavização da curva de bend; limiares nomeados (amplitude mínima, duração mínima) como
  parâmetros; slide exige mesma corda e notas adjacentes no tempo; testes com curvas sintéticas.
- Out: hammer/pull (TASK-03); export (TASK-04); bends no baixo (permitido mas sem limiar próprio).

## Done criteria

- [x] Teste: curva sintética subindo 2 semitons e sustentando vira bend de 1 tom (full); subindo 1
      semitom vira ½ tom.
- [x] Teste: oscilação ±⅓ semitom (vibrato) e ruído aleatório (seed fixa) não geram bend.
- [x] Teste: duas notas na mesma corda (casa 5 → 7) com glissando contínuo entre elas viram slide
      para cima; em cordas diferentes, não.
- [x] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Basic Pitch reporta bends em bins de ⅓ de semitom (ver `tabgen/core/transcription/basic_pitch.py`).
Registrar nas Notes os limiares escolhidos e por quê.

### Áudio de teste (YouTube)

Pode baixar áudio de músicas conhecidas no YouTube com `yt-dlp` (instalado, 2026.08.19)
para conferir a detecção em gravação real.

Candidatas com bends e slides bem audíveis (guitarra em destaque):

- Pink Floyd — "Comfortably Numb" (solos finais: bends de 1 tom e ½ tom sustentados).
- Eagles — "Hotel California" (solo final: bends e slides).
- Stevie Ray Vaughan — "Pride and Joy" (bends de blues).
- Gary Moore — "Still Got the Blues" (bends lentos, vibrato — bom para testar que vibrato não vira bend).

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

### Implementação (REF-TASK-02, 2026-10-27)

Módulo `tabgen/core/techniques/bends.py`, função pura
`detect_bends_and_slides(events, notes, config=None) -> list[TabNote]` (mesma forma da
REF-TASK-03): `notes` é paralela a `events` (nota de origem com `bends`), `ValueError` se os
tamanhos diferem, cópias via `dataclasses.replace`, técnica existente nunca é sobrescrita. O
pacote `tabgen/core/techniques/__init__.py` exporta só `BendConfig`, `detect_bends_and_slides`,
`BASIC_PITCH_FPS` e `BASIC_PITCH_BINS_PER_SEMITONE` (não importa `legato`; a REF-TASK-03/04
acrescenta o export dela).

Taxa de frames: `BASIC_PITCH_FPS = 86`, de `basic_pitch/constants.py`
(`ANNOTATIONS_FPS = AUDIO_SAMPLE_RATE // FFT_HOP = 22050 // 256`); bins de ⅓ de semitom
(`CONTOURS_BINS_PER_SEMITONE = 3`).

Ordem: slides primeiro (glissando que termina na próxima nota da mesma corda é slide, não
bend), depois bends nas notas ainda sem técnica.

Limiares (`BendConfig`, todos parâmetros nomeados) e por quê:

- `smoothing_frames = 5` (mediana, ≈ 58 ms): remove frames isolados de ruído sem achatar um
  bend real, que dura centenas de ms.
- `min_bend_semitones = 0.75`: fica entre o bin de ⅔ de semitom (2 bins: ainda ruído/vibrato
  largo) e o meio tom (3 bins); com a mediana sobre inteiros, na prática exige ≥ 3 bins.
- `min_bend_duration_s = 0.05` (5 frames): o desvio precisa ser sustentado, não um pico.
- `bend_step_semitones = 0.5`: `bend_semitones` e os pontos de `bend_curve` são arredondados a
  quarto de tom (resolução do Guitar Pro); `curve_points = 5` amostras do ataque ao fim.
- Slide: `slide_max_gap_s = 0.05` (notas adjacentes no tempo), `slide_window_s = 0.1` (cauda da
  1ª nota / cabeça da 2ª) e `min_slide_glide_semitones = 1.0` (glide mínimo na direção da outra
  nota; distingue slide de hammer/pull, que não têm glissando).

Controle (o teste falha contra a versão ingênua): com `smoothing_frames=1, min_bend_duration_s=0`
o ruído com seed 1234 e o pico curto viram bend (`test_random_pitch_noise_is_not_a_bend FAIL`,
`test_short_blip_is_not_a_bend FAIL`); com `min_bend_semitones=0.3` também o vibrato vira bend
(`vibrato low threshold FAIL`). Esse controle ficou versionado como os testes
`test_control_noise_is_a_bend_without_smoothing_and_duration` e
`test_control_vibrato_is_a_bend_with_low_amplitude_threshold`. Resultado negativo: com só
suavização desligada e amplitude padrão, o vibrato ±⅓ continua passando (a amplitude é que o
barra, não a mediana).

Limitação: no par em cordas diferentes, o glide da cauda da 1ª nota (2 semitons sustentados por
~6 frames) é classificado como bend — o teste só exige que não haja slide. Em áudio real o Basic
Pitch pode quebrar um bend/slide em notas separadas; não foi verificado (áudio do YouTube não
baixado nesta tarefa).

Verificação:

```sh
.venv/bin/pytest -q tests/test_techniques_bends.py
grep -rnE "import typer|import rich|print\(" tabgen/core/   # sem saída
.venv/bin/pytest -q && .venv/bin/ruff check .   # verdes
```

Verificação (2026-10-27, thread principal, árvore do commit sem os arquivos da REF-TASK-03):

- `.venv/bin/pytest -q tests/test_techniques_bends.py` → `15 passed in 0.02s`
- `.venv/bin/pytest -q` → `152 passed, 11 warnings`; `.venv/bin/ruff check .` → `All checks passed!`
- `grep -rnE "import typer|import rich|print\(" tabgen/core/` → vazio (exit 1)
- Controle versionado como teste: com `BendConfig(smoothing_frames=1, min_bend_duration_s=0.0)` ruído e
  blip curto viram bend; com `min_bend_semitones=0.3` o vibrato também. Resultado negativo: desligar só
  suavização e duração não faz o vibrato virar bend — quem barra o vibrato é o limiar de amplitude.
- Áudio real (YouTube) não conferido (opcional).

## Execution Log

- **Closed** — commit `8283950` (2026-10-27): feat(core): detect bends and slides from Basic Pitch pitch bends
  - Files (`git show --name-status 8283950`):
    - `M docs/rite/cycles/refinamento/02-detectar-bends-e-slides-a-partir-dos-pitch-bends.md`
    - `M docs/rite/cycles/refinamento/04-exportar-tecnicas-em-gp5-musicxml-e-ascii-e.md`
    - `A tabgen/core/techniques/__init__.py`
    - `A tabgen/core/techniques/bends.py`
    - `A tests/test_techniques_bends.py`
  - **Files amended** — added to `files`:
    - `docs/rite/cycles/refinamento/04-exportar-tecnicas-em-gp5-musicxml-e-ascii-e.md`
