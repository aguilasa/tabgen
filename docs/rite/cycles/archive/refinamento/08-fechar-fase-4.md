---
id: REF-TASK-08
---

# REF-TASK-08 — Fechar Fase 4

## Goal

A Fase 4 está verificada: técnicas aparecem no .gp5 de uma música real escolhida pelo usuário
e abrem no TuxGuitar; baixo de 5 cordas e violão nylon/aço funcionam pela CLI; o relatório de
avaliação existe com números reproduzíveis; checks e gates da fase verdes; README atualizado
(técnicas, novos presets, números de avaliação e limitações).

## Escopo

- In: rodada e2e com música real; conferência manual das técnicas no TuxGuitar pelo usuário;
  checks da Fase 4; README; venv limpa; probes e2e.
- Out: Fase 5 (web/desktop).

## Done criteria

- [x] `.venv/bin/tabgen export <música real>.mp3 -o <música>.gp5` sai 0; usuário confirma no
      TuxGuitar que bends/slides/hammer-ons aparecem (registrado nas Notes).
- [x] `.venv/bin/python scripts/probe_e2e_export.py` e `scripts/probe_e2e_sample.py` saem 0.
- [x] Todos os checks da Fase 4 do profile passam.
- [x] Venv limpa: instalação documentada sai 0 e `.venv/bin/pytest -q` verde.
- [x] README tem seção de técnicas, presets novos e tabela de avaliação com o comando que a gera.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-FMVP-006): números medidos vão ao README neste mesmo item.

### Áudio de teste (YouTube)

Pode baixar áudio de músicas conhecidas no YouTube com `yt-dlp` (instalado, 2026.08.19)
para conferir a detecção em gravação real.

Para o e2e de fechamento, uma música por elemento (o usuário pode trocar):

- Técnicas: Pink Floyd — "Comfortably Numb" (bends) e AC/DC — "Back in Black" (legato).
- Baixo de 5 cordas: Korn — "Freak on a Leash".
- Violão: Oasis — "Wonderwall" (aço) ou "Garota de Ipanema" (nylon).

Tempos e contagens que forem para o README vêm dos probes versionados; a música real serve à
confirmação manual no TuxGuitar.

O áudio fica fora do repositório (`out/` ou scratchpad, ambos ignorados; nunca versionar), é
usado só para conferência e não vira número de done criterion: pela regra do `CLAUDE.md`, arquivo
baixado não é evidência reproduzível — os critérios continuam nos testes e probes sintéticos.
Baixar só o trecho necessário (`--download-sections`) quando possível. Se o `yt-dlp` falhar ou o
vídeo não existir, trocar por outra música da lista e registrar nas Notes.

```sh
yt-dlp -x --audio-format mp3 -o 'out/audio/%(title)s.%(ext)s' "ytsearch1:<artista> <música>"
yt-dlp -x --audio-format mp3 --download-sections '*<mm:ss>-<mm:ss>' -o 'out/audio/%(title)s.%(ext)s' "ytsearch1:<artista> <música>"
```

Encaminhado pela REF-TASK-04 (2026-10-28): documentar no README `--no-techniques` (técnicas ligadas por
padrão) e as marcas ASCII `7b9`, `5/7`, `7\5`, `5h7`, `7p5` — com bend na partitura as células alargam
e as marcas aparecem com `-` (ex.: `5h--7`). O comentário desatualizado em
`tabgen/core/export/midi.py` já foi corrigido pela FIX-REF-001 (commit `4b2263e`).

Encaminhado pela REF-TASK-05 (2026-10-28): README — `--guitar-type electric|nylon|steel` (programa GM
27/24/25, casa máxima 24/19/20; programa padrão da guitarra mudou de 25 para 27), também em
`tabgen transcribe`; `--bass-tuning five-string` (B0 E1 A1 D2 G2); casas acima da 12 passam a ser
penalizadas no fretting. Os relatórios versionados em `scripts/eval/reports/` foram gerados antes
dessa mudança no fretting (tab-F1 GuitarSet 0.313 → 0.341, EGDB 0.383 → 0.418 medidos no
scratchpad): regenerar com o comando registrado na REF-TASK-06 ao fechar a fase.

Encaminhado pela REF-TASK-07 (2026-10-28): decisão em `docs/avaliacao/modelo-guitarra.md` —
recomenda adotar Riley `guitar-gaps` em tarefa nova (decisão do usuário, ainda não tomada). Ao
fechar a fase: citar o documento no README (limitações / roadmap) e atualizar o "Verificar se o
código/pesos foram liberados" do plano (Estágio 4) com o resultado (pesos públicos, MIT).
A REF-TASK-09 implementa `--transcriber riley` e decide o padrão: documentar a opção e a decisão no
README.

Encaminhado pela REF-TASK-09 (2026-10-28): README — `--transcriber basic-pitch|riley` em `export` e
`transcribe`, **padrão `riley`** (EGDB misturado: nota-F1 0,691 vs 0,615, tab-F1 0,336 vs 0,224);
primeiro uso baixa ~99 MB de pesos para o cache do `huggingface_hub`; dependências novas
`torchlibrosa==0.1.0` e `huggingface_hub`; tempo extra do riley (~+7,5 s numa música de 4 min); o
harness ganhou `--transcriber`, `--mix`, `--musdb-dir`, `--mix-dir`, `--device` e relatórios em
`scripts/eval/reports/{riley,mixed}/`. Decidir se os relatórios principais do harness (padrão do
`run.py` ainda `basic-pitch`) passam a usar o novo padrão. Tabela de tempos do README muda com o
riley como padrão. O nome do arquivo de cache da tablatura está a 2 bytes do limite de 255: um
version string maior quebra (candidato a fix).

Execução (2026-10-28):

- Downloads autorizados pelo usuário nesta sessão: 4 trechos de 60 s por `yt-dlp` em `out/audio/`
  (ignorado): Pink Floyd "Comfortably Numb (Studio Version)" 4:30–5:30 (youtube.com/watch?v=2rPKQI1KnXw),
  AC/DC "Back In Black" 0:00–1:00 (pAgnJDJN4VA), Korn "Freak On A Leash" 0:00–1:00 (jRGrNDV2mKc),
  Oasis "Wonderwall" 0:00–1:00 (bx1Bh8ZvH84). Saídas em `out/fase4/` (ignorado).
- Critério 1: `tabgen export comfortably-numb.mp3 -o …`, `back-in-black.mp3`, `freak-on-a-leash.mp3
  --bass-tuning five-string`, `wonderwall.mp3 --guitar-type steel` → rc=0 nas 4. `guitarpro.parse`:
  guitarra 482/237/357/881 notas; baixo de Freak on a Leash com 5 cordas; Wonderwall programa 25.
  Confirmação do usuário no TuxGuitar: "comfortably-numb: 1 bend, 2 slides, na guitarra e no baixo 1
  hamer; back-in-black: 1 bend e 1 slide na guitar; freak-on-a-leash: 1 bend, 2 slides e 1 hamer no
  baixo; wonderwall: 5 slides na guitar". Divergência: em Comfortably Numb contei 2 bends no
  `guitarpro.parse` e o usuário viu 1. Hammer-on de guitarra: zero nas 4 músicas (só no baixo).
  Bends poucos no solo de Comfortably Numb: com o padrão `riley`, o bend só vem quando a nota do
  Basic Pitch casa (mesmo pitch, ±50 ms).
- Critério 2: `scripts/probe_e2e_export.py` → `PASS: export exit 0 for gp5/musicxml/ascii …`;
  `scripts/probe_e2e_sample.py` → `PASS: transcribe exit 0; both .mid written …`;
  `scripts/probe_e2e_riley.py` → `PASS … basic-pitch 1.8 s, riley 4.5 s, extra +2.7 s`.
- Critério 3 (checks da Fase 4): export real sai 0 e reabre com efeitos (acima);
  `--no-techniques` em comfortably-numb → rc=0, 0 notas com efeito; `--bass-tuning five-string` →
  faixa de baixo com 5 cordas; probes acima; relatório reproduzível: `scripts/eval/run.py --dataset
  <d> --subset scripts/eval/subsets/<d>.txt` regenerou `reports/{guitarset,egdb}-*` com note-F1/tab-F1
  0.761/0.341 e 0.765/0.418; grep de pureza vazio.
- Critério 4: venv nova (Python 3.11.15 do mise) num worktree do HEAD `3c5acd6`, `pip install -e
  ".[dev]"` + `pip install --no-deps basic-pitch==0.4.0` → `install rc=0`; `pytest -q` lá →
  `221 passed`. Worktree e venv removidos. Observação: `python3.11` não está no PATH desta máquina;
  o README assume que está.
- Critério 5: README ganhou seções "Playing techniques", "Transcriber" e "Evaluation" (tabela
  limpa/mistura × basic-pitch/riley com os 4 comandos), opções `--no-techniques`, `--guitar-type`,
  `--transcriber`, preset `five-string`, programa GM 27 como padrão, linha de tempo do riley (probe).
- Critério 6: `.venv/bin/pytest -q` → `221 passed`; `ruff check .` → `All checks passed!`.
- Decisão tomada sem pergunta: o padrão do harness continua `basic-pitch` (relatórios principais =
  linha de base); o README traz as duas colunas. Pendente fora do escopo: nome do arquivo de cache
  da tablatura a 2 bytes do limite de 255 (REF-TASK-09); o plano (Estágio 4) ainda diz "Verificar
  se o código/pesos foram liberados" — atualizado abaixo.

## Execution Log

- **Closed** — commit `93adad4` (2026-10-28): docs(readme): document Phase 4 techniques, presets, transcriber and evaluation
  - Files (`git show --name-status 93adad4`):
    - `M README.md`
    - `M docs/planejamento/audio-para-tablatura.md`
    - `M docs/rite/cycles/refinamento/08-fechar-fase-4.md`
    - `M docs/rite/cycles/refinamento/progress.json`
    - `M docs/rite/cycles/refinamento/progress.md`
    - `M scripts/eval/reports/egdb-egdb.json`
    - `M scripts/eval/reports/egdb-egdb.md`
    - `M scripts/eval/reports/guitarset-guitarset.json`
    - `M scripts/eval/reports/guitarset-guitarset.md`
- **Reviewed** (2026-10-28) at `d6d1f30`: no finding
