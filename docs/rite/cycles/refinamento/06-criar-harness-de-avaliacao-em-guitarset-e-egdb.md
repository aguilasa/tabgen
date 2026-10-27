---
id: REF-TASK-06
---

# REF-TASK-06 — Criar harness de avaliação em GuitarSet e EGDB

## Goal

Existe `scripts/eval/` (ou `tabgen/eval/` fora do core) que mede a qualidade do pipeline contra
datasets anotados (plano, seção 6): GuitarSet (violão, anotação por corda) e EGDB (elétrica DI).
Para cada faixa roda transcrição (+ fretting) e calcula nota-F1 com `mir_eval.transcription`
(onset ±50 ms) e tab-F1 (nota + corda certa), gravando relatório JSON e Markdown versionáveis.

## Escopo

- In: loaders das anotações (GuitarSet JAMS; EGDB MIDI por corda); download dos datasets **fora
  do repositório** em diretório configurável (pede permissão ao usuário na execução, com tamanho
  e origem); seleção de subconjunto fixo (lista de faixas versionada) para rodar em minutos;
  relatório com médias e por faixa; teste unitário do cálculo de métricas com anotações sintéticas.
- Out: treinar modelos; otimizar o pipeline com base nos números (Fase 4 só mede).

## Done criteria

- [ ] Teste: anotação sintética idêntica à predição dá nota-F1 = 1,0 e tab-F1 = 1,0; corda trocada
      mantém nota-F1 = 1,0 e baixa tab-F1.
- [ ] `.venv/bin/python scripts/eval/run.py --dataset guitarset --subset <lista versionada>` sai 0
      e grava relatório com nota-F1 e tab-F1 médias (números nas Notes com o comando).
- [ ] Mesmo comando com `--dataset egdb` sai 0 e grava relatório (tab-F1 se a anotação permitir;
      senão registrado o motivo).
- [ ] Nenhum arquivo de áudio de dataset está versionado (`git ls-files | grep -iE "\.(wav|flac|jams)$"`
      vazio).
- [ ] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Regra do `CLAUDE.md`: números só com comando reproduzível do HEAD — o subset é versionado e o
caminho do dataset é parâmetro. Referência de números do plano: Basic Pitch ~66 nota-F1 em
gravação real; TabCNN tab-F1 ~0,75 no GuitarSet. Download é ação que exige confirmação do
usuário.

Encaminhado pela REF-TASK-03 (2026-10-27): a qualidade de hammer-on/pull-off só se mede se o dataset
tiver anotação de técnica. Pelo que se sabe dos artigos (não conferido, sem download): EGDB tem só
notas por corda, sem rótulo de técnica; Guitar-TECHS é organizado por técnica (rótulo ao menos por
arquivo). Confirmar aqui e registrar.

## Execution Log
