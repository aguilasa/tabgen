---
id: FIX-FMVP-002
---

# FIX-FMVP-002 — Medir espaço em disco no diretório do cache de modelos, não no cwd

Origin: [FMVP-TASK-03](/docs/rite/cycles/archive/fundacao-mvp/03-criar-comando-tabgen-doctor-de-verificacao-de.md)

## Problem

`check_disk_space()` em `tabgen/core/doctor.py` usa `path="."` (cwd do processo) por padrão, mas
os pesos de modelo a que o requisito de ~4 GB se refere são baixados no cache do torch/demucs sob
o home (`~/.cache/torch/hub`). Rodando `tabgen doctor` de um diretório em outro filesystem (drive
externo, mount de projeto), o veredito de espaço livre mede o disco errado — pode reportar OK com
o disco do cache sem espaço, ou falhar com o disco do cache ok. Nesta máquina ambos são o mesmo
device, então a saída atual por acaso está correta.

## Evidência

```text
$ grep -n 'path: str = "."' tabgen/core/doctor.py
124:    path: str = ".", required_bytes: int = REQUIRED_DISK_BYTES
$ .venv/bin/python -c "import torch; print(torch.hub.get_dir())" 2>/dev/null
/home/ingmar/.cache/torch/hub
```

## Root cause

Hipótese: a checagem de disco foi escrita contra o texto genérico "~4 GB de disco" da seção 8 do
plano, sem vincular ao local onde os pesos de fato caem (torch hub / cache do demucs).

## Fix

Em `tabgen/core/doctor.py`, trocar o default de `check_disk_space` para o local do cache de
modelos (ex.: `torch.hub.get_dir()`, ou o diretório pai futuro quando o download de modelos
entrar em tarefa posterior), mantendo o parâmetro `path` para os testes; `run_checks()` passa
esse default.

## Arquivos

- `tabgen/core/doctor.py`

## Verificação

```text
$ .venv/bin/python -c "import inspect; from tabgen.core import doctor; assert inspect.signature(doctor.check_disk_space).parameters['path'].default != '.', 'disk check defaults to cwd'"
```

Hoje falha com `AssertionError: disk check defaults to cwd` (vermelho); depois do fix passa
(verde).

Medido após o fix (2026-10-26):

```text
$ .venv/bin/python -c "import inspect; from tabgen.core import doctor; assert inspect.signature(doctor.check_disk_space).parameters['path'].default != '.', 'disk check defaults to cwd'"; echo "exit=$?"
exit=0
$ .venv/bin/python -c "from tabgen.core import doctor; r = doctor.check_disk_space(); print(r.ok, r.detail)"
True 896.3 GB free (need ~4 GB for model weights)
```

## Notas

Default de `check_disk_space` trocado para resolução preguiçosa: `path: str | None = None`,
resolvido dentro da função por `_model_cache_dir()`, que usa `torch.hub.get_dir()` quando o torch
está instalado e cai para `$XDG_CACHE_HOME/torch/hub` (ou `~/.cache/torch/hub`) quando não está —
seguindo o estilo do módulo de importar torch apenas dentro da função. Como o diretório de cache
pode não existir numa máquina nova, `_nearest_existing()` mede o ancestral existente mais próximo
para que `shutil.disk_usage` não levante exceção. O parâmetro `path` segue aceitando caminho
explícito, então os testes existentes (que passam `tmp_path`) não mudam.

## Execution Log

- 2026-10-26 — Triagem (`rite reproduce FIX-FMVP-002`): REPRODUCED.

  ```text
  $ grep -n 'path: str = "."' tabgen/core/doctor.py
  124:    path: str = ".", required_bytes: int = REQUIRED_DISK_BYTES
  $ .venv/bin/python -c "import torch; print(torch.hub.get_dir())" 2>/dev/null
  /home/ingmar/.cache/torch/hub
  ```
- **Closed** — commit `cb42a89` (2026-10-26): fix(doctor): measure disk space at model cache dir, not cwd
  - Files (`git show --name-status cb42a89`):
    - `M tabgen/core/doctor.py`
