---
id: FIX-ANA-001
---

# FIX-ANA-001 — Adicionar teste que guarda o wiring do check madmom em run_checks

Origin: [ANA-TASK-01](/docs/rite/cycles/analise-musical/01-validar-instalacao-do-madmom-no-venv-e-fixar.md)

## Problem

Remover `check_madmom()` de `run_checks()` em `tabgen/core/doctor.py` deixa a suíte inteira
verde: `test_cli_doctor_json_output` monkeypatcha `run_checks` com um `_passing_report()`
fabricado cuja lista fixa de nomes inclui "madmom", então nenhum teste exercita a composição
real. O done criterion "`tabgen doctor` lista uma linha do madmom" vale hoje (verificado ao
vivo) mas não tem guarda de regressão, e a lista asserida no teste da CLI engana — continuaria
afirmando "madmom" depois do check desligado.

## Evidência

Probe com defeito plantado em cópia scratch do HEAD (forçando a cópia no import, porque o
tabgen está instalado editable e sombrearia a cópia):

```text
$ T=$(mktemp -d) && git archive HEAD | tar -x -C "$T"
$ sed -i 's/check_madmom(),/# check_madmom(),/' "$T/tabgen/core/doctor.py"
$ cd "$T" && /home/ingmar/development/tabgen/.venv/bin/python - <<'EOF'
import sys
sys.meta_path = [f for f in sys.meta_path if 'editable' not in getattr(type(f), '__module__', '').lower()]
sys.path.insert(0, '.')
import tabgen; print('tabgen from:', tabgen.__file__)
import pytest
sys.exit(pytest.main(['-q', 'tests/test_doctor.py']))
EOF
tabgen from: <scratch>/tabgen/__init__.py
13 passed in 1.17s
```

Suíte verde com o check do madmom desligado de `run_checks` — nenhum teste pega a regressão.

## Root cause

Hipótese: `test_cli_doctor_json_output` é anterior à task e testa só apresentação, stubando
`run_checks`; a task adicionou testes presente/ausente de `check_madmom` (como as Notes dizem),
mas nenhum teste chama o `run_checks()` real, então a composição ficou sem cobertura.

## Fix

Em `tests/test_doctor.py`, adicionar teste que chama o `doctor.run_checks()` real e assere que
existe um check chamado "madmom" e essencial (`check_madmom` retorna `CheckResult` mesmo com
madmom ausente, então o teste é seguro em qualquer ambiente).

## Arquivos

- `tests/test_doctor.py`

## Verificação

```text
$ grep -n "doctor.run_checks()" tests/test_doctor.py
```

Sai 1 hoje (nenhum teste toca o `run_checks` real); deve sair 0 depois do fix, e o novo teste
deve passar em `.venv/bin/pytest -q tests/test_doctor.py`.

## Execution Log
