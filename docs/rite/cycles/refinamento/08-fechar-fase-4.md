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

- [ ] `.venv/bin/tabgen export <música real>.mp3 -o <música>.gp5` sai 0; usuário confirma no
      TuxGuitar que bends/slides/hammer-ons aparecem (registrado nas Notes).
- [ ] `.venv/bin/python scripts/probe_e2e_export.py` e `scripts/probe_e2e_sample.py` saem 0.
- [ ] Todos os checks da Fase 4 do profile passam.
- [ ] Venv limpa: instalação documentada sai 0 e `.venv/bin/pytest -q` verde.
- [ ] README tem seção de técnicas, presets novos e tabela de avaliação com o comando que a gera.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

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
e as marcas aparecem com `-` (ex.: `5h--7`). Comentário desatualizado em
`tabgen/core/export/midi.py:37-38` continua pendente (edição recusada pelo sistema de permissões;
decisão do usuário).

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

## Execution Log
