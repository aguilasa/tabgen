---
id: REF-TASK-07
---

# REF-TASK-07 — Avaliar modelo de transcrição específico de guitarra

## Goal

Há uma decisão registrada, com números do harness (TASK-06), sobre substituir o estágio 4 por
um modelo específico de guitarra (plano, Estágio 4: Riley et al. 2024; TART): verificar se código e
pesos estão públicos e com licença compatível; se sim, rodar no mesmo subset e comparar com o
Basic Pitch; entregar recomendação. A troca em si não faz parte (decisão do usuário).

## Escopo

- In: levantamento de disponibilidade e licença (Riley 2024, TART, YourMT3+ como controle);
  wrapper experimental fora do core (`scripts/eval/`) para o candidato disponível; comparação no
  subset do harness; documento de decisão em `docs/`.
- Out: integrar o modelo ao `core`/CLI (tarefa nova se a recomendação for trocar).

## Done criteria

- [ ] Documento `docs/avaliacao/modelo-guitarra.md` existe com: links e licenças verificados, tabela
      nota-F1/tab-F1 de Basic Pitch vs candidato(s) no mesmo subset, comando que gera cada número e
      recomendação.
- [ ] Se nenhum candidato tiver código/pesos públicos, o documento registra a verificação (URLs e
      data) e a recomendação é manter o Basic Pitch.
- [ ] `.venv/bin/pytest -q` verde (o wrapper experimental não entra no core).

## Notes

Licença: modelos non-commercial são aceitos (plano, seção 4); AGPL evitada. Downloads de pesos
exigem confirmação do usuário.

## Execution Log
