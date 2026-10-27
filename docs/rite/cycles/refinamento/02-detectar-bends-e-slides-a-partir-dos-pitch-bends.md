---
id: REF-TASK-02
---

# REF-TASK-02 — Detectar bends e slides a partir dos pitch bends

## Goal

Existe `tabgen/core/techniques/bends.py` (ou módulo equivalente em `core/`): a partir dos pitch
bends por nota, classifica bend (desvio sustentado ≥ ½ tom acima do pitch, com retorno opcional)
e slide (transição contínua entre duas notas consecutivas na mesma corda com glissando de pitch),
preenchendo a técnica da `TabNote`. Vibrato curto e ruído de pitch não viram bend.

## Escopo

- In: suavização da curva de bend; limiares nomeados (amplitude mínima, duração mínima) como
  parâmetros; slide exige mesma corda e notas adjacentes no tempo; testes com curvas sintéticas.
- Out: hammer/pull (TASK-03); export (TASK-04); bends no baixo (permitido mas sem limiar próprio).

## Done criteria

- [ ] Teste: curva sintética subindo 2 semitons e sustentando vira bend de 1 tom (full); subindo 1
      semitom vira ½ tom.
- [ ] Teste: oscilação ±⅓ semitom (vibrato) e ruído aleatório (seed fixa) não geram bend.
- [ ] Teste: duas notas na mesma corda (casa 5 → 7) com glissando contínuo entre elas viram slide
      para cima; em cordas diferentes, não.
- [ ] `grep -rnE "import typer|import rich|print\(" tabgen/core/` não retorna nada.
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Basic Pitch reporta bends em bins de ⅓ de semitom (ver `tabgen/core/transcription/basic_pitch.py`).
Registrar nas Notes os limiares escolhidos e por quê.

## Execution Log
