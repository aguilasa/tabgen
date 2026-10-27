---
id: TAB-TASK-08
---

# TAB-TASK-08 — Fechar Fase 3

## Goal

A Fase 3 está verificada com música real: `tabgen export` gera .gp5 de uma gravação escolhida
pelo usuário, o arquivo abre no TuxGuitar (e/ou Guitar Pro) com faixas guitarra e baixo, tempos
medidos, checks e gates da fase verdes, README atualizado com uso e tempos do `export`.

## Escopo

- In: rodada e2e com música real; tempos frio/quente com o comando de medição; verificação
  manual no TuxGuitar pelo usuário; checks da Fase 3; README (uso, exemplo de ASCII, tempos,
  limitações da seção 7); venv limpa.
- Out: melhorias de qualidade (Fase 4).

## Done criteria

- [ ] `.venv/bin/tabgen export <música real>.mp3 -o <música>.gp5` sai 0 na GPU; tempos frio e quente
      anotados com o comando de medição.
- [ ] Usuário confirma que o .gp5 abre no TuxGuitar com faixas guitarra e baixo (registrado nas
      Notes).
- [ ] Todos os checks da Fase 3 do profile passam.
- [ ] Venv limpa: instalação documentada sai 0 e `.venv/bin/pytest -q` verde.
- [ ] README tem seção do `export` com tempos medidos e as limitações (rascunho editável).
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-FMVP-006): números medidos no e2e vão para o README neste mesmo item.

Encaminhado pela TASK-07 (2026-10-27): opções do `export` para o README —
`-o FILE` (formato pelo sufixo `.gp5`/`.musicxml`/`.xml`/`.txt`), `--format gp5|musicxml|ascii`,
`--instruments guitar,bass`, `--tuning`/`--bass-tuning` (preset ou notas low-to-high, ex.
`D2,A2,D3,G3,B3,E4`), `--capo N` (só guitarra), `--device`. Medida parcial com caches
upstream quentes (`You and I.flac`): estágio tablatura frio 0.58 s, cache hit 0.35 s — o tempo
frio completo (separação + análise + transcrição + tablatura) ainda precisa ser medido aqui.

## Execution Log
