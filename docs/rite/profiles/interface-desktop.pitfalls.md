# Measured pitfalls — interface-desktop

<!--
One entry per pitfall. Commands search this file by tag or path; it is never read whole.
Format:

### <short title>
- tags: <tag>, <tag>
- paths: <glob>
- proven by: <FIX-ID or commit> (<YYYY-MM-DD>)
- rule: <what to do instead, in one sentence>
-->

### Cache hit valida identidade do artefato, não só existência
- tags: cache, stems, separation
- paths: tabgen/core/**
- proven by: FIX-FMVP-004 (2026-10-26)
- rule: quando o artefato cacheado vive em caminho compartilhado entre inputs, gravar identidade (tamanho + mtime_ns ou hash) no payload e comparar no hit.

### Checagem de recurso mede onde o recurso vive
- tags: doctor, disk, paths
- paths: tabgen/core/doctor.py
- proven by: FIX-FMVP-002 (2026-10-26)
- rule: nunca usar cwd como default para checar disco/cache; resolver o diretório real (ex.: `torch.hub.get_dir()`) e medir o ancestral existente mais próximo.

### Números em Notes/README exigem probe versionado
- tags: verification, numbers, readme, e2e
- paths: README.md, docs/rite/cycles/**, scripts/**
- proven by: FIX-FMVP-005, FIX-FMVP-006 (2026-10-26), FIX-TAB-005 (2026-10-27)
- rule: todo número publicado vem com o comando versionado que o gera (incl. geração da amostra) e afirma só fatos estáveis; após um e2e real, atualizar no mesmo item os documentos que citavam estimativas. Cada comando de e2e (`separate`, `transcribe`, `analyze`, `export`) tem probe em `scripts/probe_e2e_*.py` sobre amostra gerada; arquivo de scratchpad não é evidência.

### Gates chamam binários do venv
- tags: gates, venv, tooling
- paths: docs/rite/profiles/*.md, rite.toml
- proven by: FIX-FMVP-003 (2026-10-26)
- rule: comandos de gate usam `.venv/bin/<tool>`, pois `rite gates` roda em bash limpo sem venv no PATH.

### .gitignore sem comentário inline
- tags: gitignore
- paths: .gitignore
- proven by: FIX-FMVP-001 (2026-10-26)
- rule: comentário em `.gitignore` só em linha própria; validar com `git check-ignore -v <caminho>`.

### Emendar files declarados antes de commitar fora do escopo
- tags: bookkeeping, files, scope
- paths: docs/rite/cycles/**
- proven by: FIX-FMVP-007 (2026-10-26), FIX-ANA-002 (2026-10-27), FIX-TAB-004, FIX-TAB-006 (2026-10-27), FIX-REF-002 (2026-10-28)
- rule: antes do `rite finish`, comparar os `files` do item com `git show --stat` do work commit nos dois sentidos (tocado fora da lista, listado e não tocado) e corrigir com `rite set <ID> --files ...`. A regra do `CLAUDE.md` sozinha não bastou: rodar a comparação como último passo antes do `rite finish`, não de memória.

### Teste da composição real, não só do stub
- tags: tests, mocks, doctor, pipeline
- paths: tests/**
- proven by: FIX-ANA-001 (2026-10-26)
- rule: ao adicionar um item a uma função que compõe uma lista (checks, estágios), ter um teste que chama a função real sem monkeypatch e assere o item; provar com defeito plantado.

### Convenção de contrato fica no contrato, não em prosa de tarefa
- tags: contract, models, conventions
- paths: tabgen/core/models.py, tabgen/core/**
- proven by: FIX-TAB-001 (2026-10-27), FIX-REF-001 (2026-10-28)
- rule: quando uma tarefa produz valores de um campo cuja semântica outra tarefa definiu (ex.: numeração de corda), conferir e alinhar o docstring do contrato no mesmo commit; encaminhamento em Notes de tarefa fechada não conta. O mesmo vale para qualquer pendência da tarefa (edição negada pela permissão, comentário a corrigir): ou é feita, ou vira fix pela CLI (`rite new-fix`), ou a tarefa fica blocked — nunca só em Notes/Execution Log.

### Comparar valores parseados, não strings renderizadas
- tags: analysis, key, labels, external-lib
- paths: tabgen/core/analysis/**
- proven by: FIX-TAB-002 (2026-10-27)
- rule: igualdade de rótulos musicais (tom, acorde) compara `(pitch_class, mode)`/campos parseados; grafia canônica casa com a da lib que produz o rótulo, testada por modo.

### Saída citada é colada, não digitada
- tags: verification, notes
- paths: docs/rite/cycles/**
- proven by: FIX-TAB-003 (2026-10-27)
- rule: linha de saída citada em Verificação/Notes é cópia literal do terminal.

### Check de fase só cita recurso já entregue ou marcado com a tarefa dona
- tags: profile, phase-checks, review
- paths: docs/rite/profiles/*.md
- proven by: FIX-REF-003 (2026-10-28)
- rule: ao escrever checks de fase no planejamento, anotar a tarefa que entrega cada recurso citado (ex.: "(REF-TASK-05)"); revisor que encontra o check vermelho com a tarefa dona pendente registra nota, não fix.
