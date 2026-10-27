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

## Execution Log
