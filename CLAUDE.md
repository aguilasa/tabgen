<!-- rite:begin -->
Este repositório usa **Rite** para gerir o trabalho; configuração em `rite.toml`.
Estado de tarefas/fixes muda **somente** pela CLI do Rite (nunca editar `progress.json`/`fixes.json` à mão).
Comandos: `/rite:status`, `/rite:new-cycle`, `/rite:plan-to-tasks`, `/rite:execute`, `/rite:review`, `/rite:fix`.
Ciclos em `docs/rite/cycles/`; profiles em `docs/rite/profiles/`; planos em `docs/plans/`.
Idiomas: documentação do Rite em pt-BR; código e commits em inglês (en-US), estilo conventional.
<!-- rite:end -->

Regras promovidas das retros do Rite:
- Antes de `rite finish`, comparar os `files` do item com `git show --stat` do work commit nos dois sentidos (arquivo tocado fora da lista, arquivo listado e não tocado) e corrigir com `rite set <ID> --files …` (FIX-FMVP-007, FIX-ANA-002, FIX-TAB-004, FIX-TAB-006).
- Número de verificação e2e só vale com comando reproduzível a partir do HEAD: probe em `scripts/probe_e2e_*.py` sobre amostra gerada; arquivo de scratchpad não é evidência (FIX-FMVP-005, FIX-FMVP-006, FIX-TAB-005).
- Pendência que a tarefa não conclui (edição negada pela permissão, decisão encaminhada) vira fix pela CLI (`rite new-fix`) ou deixa a tarefa blocked; nunca fica só em prosa de tarefa fechada (FIX-TAB-001, FIX-REF-001).
