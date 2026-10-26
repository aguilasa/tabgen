---
id: ANA-TASK-06
---

# ANA-TASK-06 — Fechar Fase 2

## Goal

A Fase 2 está verificada com música real: `tabgen analyze` roda de ponta a ponta na GPU sobre
uma gravação escolhida pelo usuário, tempos medidos, checks e gates da fase verdes, e README
atualizado com uso e tempos medidos do `analyze`.

## Escopo

- In: rodada e2e com música real; tempos por estágio com o comando que os mede; conferência
  manual do tom/BPM/acordes pelo usuário; checks da Fase 2 do profile; README (uso, exemplo de
  saída, tempos medidos); `doctor` e instalação em venv limpa.
- Out: melhorias de qualidade (Fase 4); novos recursos.

## Done criteria

- [ ] `.venv/bin/tabgen analyze <música real>.mp3` sai 0 na GPU; tempos (frio e quente) anotados
      com o comando de medição.
- [ ] Usuário confirma tom e BPM da música real (verificação manual registrada nas Notes).
- [ ] Todos os checks da Fase 2 do profile passam.
- [ ] Venv limpa: instalação documentada (incl. madmom) sai 0 e `.venv/bin/pytest -q` verde.
- [ ] `! grep -qi "will be added" README.md` e README tem seção do `analyze` com tempos medidos.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-FMVP-006): números medidos no e2e vão para o README neste mesmo item, não
depois.

## Execution Log
