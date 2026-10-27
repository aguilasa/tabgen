# Measured pitfalls — tablatura

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
- proven by: FIX-FMVP-005, FIX-FMVP-006 (2026-10-26)
- rule: todo número publicado vem com o comando versionado que o gera (incl. geração da amostra) e afirma só fatos estáveis; após um e2e real, atualizar no mesmo item os documentos que citavam estimativas.

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
- proven by: FIX-FMVP-007 (2026-10-26), FIX-ANA-002 (2026-10-27)
- rule: antes do `rite finish`, comparar os `files` do item com `git show --stat` do work commit nos dois sentidos (tocado fora da lista, listado e não tocado) e corrigir com `rite set <ID> --files ...`.

### Teste da composição real, não só do stub
- tags: tests, mocks, doctor, pipeline
- paths: tests/**
- proven by: FIX-ANA-001 (2026-10-26)
- rule: ao adicionar um item a uma função que compõe uma lista (checks, estágios), ter um teste que chama a função real sem monkeypatch e assere o item; provar com defeito plantado.
