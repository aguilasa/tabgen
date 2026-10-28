---
id: UI-TASK-04
---

# UI-TASK-04 — Implementar workspace com progresso por estágio e cancelamento

## Goal

O workspace existe conforme o protótipo: cabeçalho com "Gerar tab ▶", cartões de estágio
(pendente/cache/rodando/ok/erro) e painel de execução com uma barra por estágio real do core
(`separation`…`export`), alimentadas pelos eventos NDJSON do worker; "Cancelar" encerra o
processo worker e marca o estado; erro de estágio aparece com a mensagem da exceção.

## Escopo

- In: spawn do worker com a requisição `tablature` (opções padrão nesta task); consumo dos
  eventos progress em tempo real; estados dos cartões derivados dos estágios; kill do processo no
  cancelar; exibição de `{"type":"error"}` com kind/message; estado "cache hit" (estágios a 100
  de imediato).
- Out: abas de resultados (05); painel de opções (06 — aqui o botão roda com defaults).

## Done criteria

- [ ] Com a amostra sintética fria, as barras avançam na ordem real dos estágios e terminam
      todas em 100; resultado aparece (screenshot nas Notes).
- [ ] Segunda execução (quente) mostra cache em <5 s.
- [ ] Cancelar durante a separação encerra o processo (worker some do `ps`) e o estado fica
      "cancelado"; rodar de novo reusa o cache dos estágios concluídos.
- [ ] Erro simulado (ex.: caminho de Python sem madmom) aparece com kind e mensagem.
- [ ] `npm run build` e typecheck do frontend saem 0.

## Notes

Mapa estágio→barra segue a ordem de `_tablature_stages` (worker repassa os nomes reais;
nada hardcoded fora da ordem de exibição).

Da UI-TASK-03: `desktop/src/screens/Musica.tsx` é cabeçalho + placeholder; após um pipeline,
atualizar `processed_at` e `artifacts` da entrada em `desktop/src/lib/recents.ts` (pelo caminho;
ainda não há função para isso). Para abrir uma música sem o picker num teste headless, há
`TABGEN_OPEN=<caminho>` (só debug). Verificação de GUI só em Xvfb, nunca no display do usuário.

## Execution Log
