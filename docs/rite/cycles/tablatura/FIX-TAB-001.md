---
id: FIX-TAB-001
---

# FIX-TAB-001 — Reconcile TabNote string numbering with fretting stage convention

Origin: [TAB-TASK-01](/docs/rite/cycles/tablatura/01-definir-contrato-tabscore-completo.md)

## Problem

O contrato `TabNote` (`tabgen/core/models.py`) define `string` 1-based com corda 1 = mais
**grave** (mesma ordem de `tuning_midi`), mas o estágio de fretting (`tabgen/core/fretting/dp.py`,
único produtor de valores corda/casa) emite a convenção de guitarrista: corda 1 = mais **aguda**,
corda N = mais grave. O doc da TAB-TASK-03 registra o conflito como "encaminhado para
reconciliação na revisão/TASK-05", mas o documento da TASK-05 não contém nenhum traço disso.
Se a TASK-07 ligar a saída do fretting em `TabScore` sem conversão, toda tablatura exportada sai
espelhada verticalmente (notas nas cordas erradas). A convenção escolhida no contrato também é o
oposto do que guitarristas e leitores de .gp5/MusicXML esperam.

Achado por duas revisões independentes: TAB-TASK-01 (high) e TAB-TASK-03 (medium) — mesma raiz.

## Evidência

Revisão de TAB-TASK-01:

```text
$ grep -n "lowest-pitched" tabgen/core/models.py
110:# (index 0 = lowest-pitched/thickest string).
119:    # String index, 1-based, where 1 is the lowest-pitched string

$ grep -n "highest" tabgen/core/fretting/dp.py
14:the **highest**-pitched string and string ``N`` the lowest (for standard
109:    ``string`` is 1-based with string 1 = highest-pitched string (guitarist

$ sed -n '74,77p' docs/rite/cycles/tablatura/03-atribuir-corda-e-casa-por-programacao-dinamica.md
  mais grave, corda 1 = mais aguda), ou seja `string = n_cordas − índice_low_to_high`.
  Atenção: o docstring de `TabNote` em `models.py` diz o oposto ("string 1 = lowest-pitched");
  conflito encaminhado para reconciliação na revisão/TASK-05 (não editei `models.py`).
```

Revisão de TAB-TASK-03 (confirma que o encaminhamento prometido não existe na TASK-05):

```text
$ grep -n "TabNote\|convenção\|convention\|corda 6\|highest\|lowest" docs/rite/cycles/tablatura/05-exportar-gp5-via-pyguitarpro.md
(sem saída — nada registrado para a TASK-05)
```

## Root cause

Hipótese: TAB-TASK-01 escolheu "corda 1 = mais grave" para espelhar a ordem low-to-high de
`tuning_midi` sem conferir a convenção de guitarrista exigida depois pelos done criteria da
TASK-03; nenhuma das duas tasks atualizou o contrato, e o encaminhamento ficou só como prosa na
task fechada.

## Fix

Decidir uma convenção e fazer o contrato declará-la. Resolução natural: adotar a convenção de
guitarrista já implementada e testada em `tabgen/core/fretting/dp.py` — corrigir o comentário de
`TabNote.string` (`tabgen/core/models.py:119-120`), a nota "Convenção de corda" do doc da
TAB-TASK-01 e os valores de exemplo em `tests/test_models.py` (semântica apenas; sem mudança de
campos). Se o usuário decidir pelo outro lado, inverter os docstrings de `dp.py` e o mapeamento
na integração (`string = n_strings + 1 - s`). Estado do Rite só via CLI
(`sh "$RITE_HOME/bin/rite"`); nunca editar `progress.json`/`fixes.json` à mão.

## Arquivos

- tabgen/core/models.py
- tests/test_models.py
- tabgen/core/fretting/dp.py
- docs/rite/cycles/tablatura/01-definir-contrato-tabscore-completo.md

## Verificação

```text
! grep -q "1 is the lowest-pitched string" tabgen/core/models.py
```

Falha agora (contrato diz lowest); passa quando o contrato adotar a convenção do fretting — ou,
se a decisão for inversa, trocar o check por `! grep -q "highest-pitched string (guitarist" tabgen/core/fretting/dp.py`.
Depois: `.venv/bin/pytest -q` verde e `sh "$RITE_HOME/bin/rite" check --quick --json` com 0 erros.

## Execution Log

- 2026-10-27 — Triagem inline (`rite reproduce --all --cycle tablatura`): REPRODUCED. Saída atual
  idêntica à Evidência: `grep -n "lowest-pitched" tabgen/core/models.py` → linhas 110 e 119
  ("1 is the lowest-pitched string"); `grep -n "highest" tabgen/core/fretting/dp.py` → linhas 14
  e 109 ("string 1 = highest-pitched string (guitarist"); grep na TASK-05 → exit 1 (sem traço do
  encaminhamento). Conflito de convenção segue presente no HEAD.
- 2026-10-27 — Fix aplicado: adotada a convenção de guitarrista (corda 1 = mais aguda, corda N =
  mais grave), já implementada e testada em `tabgen/core/fretting/dp.py`. Mudanças (semântica
  apenas, sem alterar campos): comentário de `TabNote.string` em `tabgen/core/models.py:119-122`
  reescrito declarando a convenção e a ordem inversa em relação a `tuning_midi` (o comentário da
  linha 110, sobre a ordem low-to-high dos presets de afinação, está correto e foi mantido); nota
  "Convenção de corda" do doc da TAB-TASK-01 corrigida com Adendo referenciando este fix;
  `tests/test_models.py` inspecionado — nenhum valor ou comentário ilustra a convenção antiga
  (valores de string/fret são dados de round-trip válidos em ambas), nada a mudar; `dp.py` já
  declara a convenção adotada, sem edição. Verificação: `! grep -q "1 is the lowest-pitched
  string" tabgen/core/models.py` falhava antes e passa depois; `.venv/bin/pytest
  tests/test_models.py -q` → 21 passed; `.venv/bin/ruff check .` → All checks passed!. A suíte
  completa acusa 6 falhas em `tests/test_key_check.py`, arquivo em edição paralela pelo
  FIX-TAB-002 (fora do escopo deste item e sem relação com mudança só de comentários/docs).
- 2026-10-27 — Verificação final na árvore do commit (FIX-TAB-002 em stash):
  `! grep -q "1 is the lowest-pitched string" tabgen/core/models.py` passa;
  `.venv/bin/pytest -q` → 105 passed; `.venv/bin/ruff check .` → All checks passed!;
  `rite gates --id FIX-TAB-001` → passed (0 gates configurados no profile).
