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

Medido após o fix (2026-10-26):

```text
$ .venv/bin/pytest -q tests/test_doctor.py
14 passed
$ <probe de defeito plantado, cópia scratch do HEAD + teste novo, check_madmom() comentado>
FAILED tests/test_doctor.py::test_run_checks_includes_essential_madmom_check
1 failed, 13 passed  (probe_exit=1)
```

## Notas

Teste novo `test_run_checks_includes_essential_madmom_check` chama o `doctor.run_checks()` real
(sem monkeypatch) e assere check "madmom" presente e essencial — seguro com madmom ausente
(`check_madmom` sempre retorna `CheckResult`). Probe de defeito plantado: verde antes do fix
(13 passed com o check desligado), vermelho depois exatamente no teste novo. O grep da
Verificação original era fraco (já casava 1 ocorrência no HEAD); o probe é o critério decisivo.

## Execution Log

- 2026-10-26 — Triagem: runner inline não decide (cada linha da Evidência roda em shell
  separado, `$T` não persiste). Agente reprodutor rodou como script único: REPRODUCED.

  ```text
  sed: linha 211 vira `# check_madmom(),` (mutação aplicada)
  tabgen from: /tmp/tmp.h0btdCTC7p/tabgen/__init__.py (cópia scratch, sem sombra do editable)
  pytest: 13 passed in 1.24s (exit 0) na cópia mutada — sem guarda de regressão
  ```

  Nota: `grep -c "doctor.run_checks()" tests/test_doctor.py` = 1 já no HEAD — o comando da
  Verificação deste fix é fraco (já casa hoje); o critério decisivo é o probe de defeito
  plantado passar a falhar depois do fix.
- **Closed** — commit `2296b4a` (2026-10-26): test(doctor): guard check_madmom wiring in run_checks
  - Files (`git show --name-status 2296b4a`):
    - `M tests/test_doctor.py`
