---
id: FIX-REF-003
---

# FIX-REF-003 — Phase check --bass-tuning five-string does not run: preset missing

Origin: [REF-TASK-06](/docs/rite/cycles/refinamento/06-criar-harness-de-avaliacao-em-guitarset-e-egdb.md)

## Problem

O check de Fase 4 do profile manda `--bass-tuning five-string` gerar faixa de baixo de 5 cordas,
mas a CLI rejeita o valor ("Invalid option: invalid note name in tuning: 'five-string'", exit 2);
`TUNING_PRESETS["bass"]` em `tabgen/core/pipeline.py` (linhas 339–343) só tem standard, drop-d e
half-step-down. O recurso funciona com afinação explícita (`--bass-tuning "B0,E1,A1,D2,G2"` sai 0
e o .gp5 reabre com 5 cordas), mas nenhum teste nem probe cobre o check como escrito. Dois
revisores independentes (REF-TASK-04 e REF-TASK-06) mediram o check vermelho no HEAD; o suporte a
baixo de 5 cordas é escopo da REF-TASK-05, ainda pendente — este fix cobre o descompasso
profile × código até lá.

## Evidência

```text
$ ffmpeg -y -f lavfi -i "sine=frequency=220:duration=10" -q:a 2 /tmp/x/sample.mp3 && .venv/bin/tabgen export /tmp/x/sample.mp3 -o /tmp/x/out5.gp5 --bass-tuning five-string; echo "exit=$?"
Invalid option: invalid note name in tuning: 'five-string'
exit=2

$ grep -n "five" tabgen/core/pipeline.py
(vazio)
```

## Root cause

Hipótese: o profile foi escrito com um nome de preset que nunca existiu (ou a tarefa de suporte a
5 cordas deveria adicionar o preset "five-string" e ainda não o fez — REF-TASK-05 pendente). Não
é possível provar qual dos dois sem a execução da REF-TASK-05.

## Fix

Uma de duas direções (decisão do usuário):
1. Adicionar o preset `"five-string"` (`[23, 28, 33, 38, 43]`) em `TUNING_PRESETS["bass"]`
   (`tabgen/core/pipeline.py`) com teste — natural se a REF-TASK-05 for entregá-lo mesmo;
2. Corrigir o texto do check em `docs/rite/profiles/refinamento.md` para a sintaxe real
   (`--bass-tuning "B0,E1,A1,D2,G2"`).
Se a REF-TASK-05 entregar o preset, marcar este fix stale com
`sh "$RITE_HOME/bin/rite" mark-stale FIX-REF-003 --reason "…"` após verificar.

## Arquivos

- tabgen/core/pipeline.py
- docs/rite/profiles/refinamento.md

## Verificação

```text
ffmpeg -y -f lavfi -i "sine=frequency=220:duration=10" -q:a 2 /tmp/x/sample.mp3 && .venv/bin/tabgen export /tmp/x/sample.mp3 -o /tmp/x/out5.gp5 --bass-tuning five-string && .venv/bin/python -c "import guitarpro,sys; song=guitarpro.parse('/tmp/x/out5.gp5'); sys.exit(0 if any('bass' in t.name.lower() and len(t.strings)==5 for t in song.tracks) else 1)"
```

Falha hoje no export (exit 2); deve sair 0 após o fix — ou, se o fix for no profile, o comando
corrigido do profile deve sair 0.

Nota (2026-10-28): o preset `five-string` em `--bass-tuning` entrou com a REF-TASK-05 (commit desta
task); falta rodar a Verificação desta fix (usa Demucs real).

## Execution Log

- **Stale** (2026-10-28) at `359be68`: tabgen export sample.mp3 -o out5.gp5 --bass-tuning five-string now exits 0 with bass tuning [23, 28, 33, 38, 43]; grep five tabgen/core/pipeline.py shows the preset at line 357
