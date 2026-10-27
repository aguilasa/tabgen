---
id: REF-TASK-01
---

# REF-TASK-01 — Definir contrato de técnicas de guitarra

## Goal

Os contratos carregam técnicas de guitarra: `Note` (`tabgen/core/models.py`) ganha os pitch
bends do Basic Pitch (hoje só em `TranscriptionResult.bends`, fora do contrato), e `TabNote` ganha
um campo de técnica tipado — bend (semitons alvo e curva simplificada), slide (para cima/baixo,
nota de destino), hammer-on, pull-off — serializável em JSON e com round-trip testado.

## Escopo

- In: campo `bends` opcional em `Note` (lista de bins 1/3 de semitom ou `None`) com transcrição
  passando a preenchê-lo; dataclass de técnica em `TabNote` (default: nenhuma); `from_dict`
  retrocompatível (JSON sem os campos novos carrega); versão de formato do contrato incrementada
  nas chaves de cache que o usam.
- Out: detecção (TASK-02/03); export (TASK-04); palm mute (decidido fora, precisa de classificador).

## Done criteria

- [ ] `.venv/bin/pytest -q tests/test_models.py` verde, com round-trip de `TabScore` cujas notas têm
      bend, slide, hammer-on e pull-off, e de `NoteEvents` com bends.
- [ ] Teste: JSON gerado antes da mudança (fixture versionada sem os campos novos) carrega com
      `from_json` e técnicas vazias.
- [ ] Teste: a versão de cache de transcrição e de tablatura muda (entrada antiga vira miss).
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-TAB-001): a convenção de cada campo novo fica no docstring do contrato, não
em prosa de tarefa. Pitfall "Cache hit valida identidade": contrato muda ⇒ versão de cache muda.

## Execution Log
