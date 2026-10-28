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

- [x] Teste: anotação sintética idêntica à predição dá nota-F1 = 1,0 e tab-F1 = 1,0; corda trocada
      mantém nota-F1 = 1,0 e baixa tab-F1.
- [x] `.venv/bin/python scripts/eval/run.py --dataset guitarset --subset <lista versionada>` sai 0
      e grava relatório com nota-F1 e tab-F1 médias (números nas Notes com o comando).
- [x] Mesmo comando com `--dataset egdb` sai 0 e grava relatório (tab-F1 se a anotação permitir;
      senão registrado o motivo).
- [x] Nenhum arquivo de áudio de dataset está versionado (`git ls-files | grep -iE "\.(wav|flac|jams)$"`
      vazio).
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Regra do `CLAUDE.md`: números só com comando reproduzível do HEAD — o subset é versionado e o
caminho do dataset é parâmetro. Referência de números do plano: Basic Pitch ~66 nota-F1 em
gravação real; TabCNN tab-F1 ~0,75 no GuitarSet. Download é ação que exige confirmação do
usuário.

Encaminhado pela REF-TASK-03 (2026-10-27): a qualidade de hammer-on/pull-off só se mede se o dataset
tiver anotação de técnica. Pelo que se sabe dos artigos (não conferido, sem download): EGDB tem só
notas por corda, sem rótulo de técnica; Guitar-TECHS é organizado por técnica (rótulo ao menos por
arquivo). Confirmar aqui e registrar.

Implementação (2026-10-28):

- Arquivos: `scripts/eval/{__init__,run,metrics,loaders,download}.py`, subsets versionados em
  `scripts/eval/subsets/{guitarset,egdb}.txt` (8 faixas cada), teste `tests/test_eval_metrics.py`.
  `loaders.py` e `download.py` foram acrescentados à lista de arquivos prevista.
- Métricas (`metrics.py`): nota-F1 = `mir_eval.transcription.precision_recall_f1_overlap` com
  onset ±50 ms, pitch ±50 cents, sem critério de offset. Tab-F1 usa o mesmo casamento
  (`mir_eval.transcription.match_notes`, que ignora a corda); um par casado só conta como acerto de
  tab se a corda estimada for igual à de referência (com altura e corda iguais, a casa fica implícita).
  Precisão = acertos/estimadas, revocação = acertos/referência; logo tab-F1 ≤ nota-F1. Nota que o
  fretting deixou sem corda (`unassigned`) conta para nota-F1, nunca para tab-F1.
- Convenção de cordas: tudo é convertido para a do tabgen (corda 1 = mi agudo, 6 = mi grave).
  GuitarSet: `annotation_metadata.data_source` 0..5 = mi grave..mi agudo (convenção do mirdata),
  portanto corda = 6 − índice. O JAMS é lido como JSON puro, sem o pacote `jams`.
- EGDB: o README do dataset diz apenas que os rótulos trazem "pitch onset and string"; a codificação
  da corda no MIDI não está documentada e não foi conferida sem download. O loader agrupa as notas
  por trilha MIDI (ou por canal, se for uma trilha só) e escolhe o mapeamento grupo→corda (ordem
  crescente ou decrescente, com qualquer deslocamento) que deixa mais notas tocáveis (casa 0..24,
  afinação padrão). Se esse mapeamento não for único ou ficar abaixo de 95% de notas tocáveis, a
  tab-F1 da faixa vira `n/a` e o relatório registra o motivo. O mapeamento escolhido sai no
  relatório, por faixa.
- Pipeline avaliado: `transcribe` do Basic Pitch direto no arquivo (o mono-mic do GuitarSet e o DI
  do EGDB já são só guitarra, então não há separação), seguido de `assign_frets` com
  `guitar_config()` (afinação padrão). As duas etapas podem ser injetadas (`run.main(...,
  estimator=...)`) para teste. O cache de estágio do Basic Pitch fica ao lado do áudio, ou seja,
  dentro do diretório do dataset e fora do repositório.
- Datasets ficam fora do repositório, em `--data-dir` (padrão `$TABGEN_DATASETS/<dataset>`, senão
  `~/datasets/tabgen/<dataset>`). `--download` só imprime as URLs e os tamanhos do que falta para o
  subset; o download só acontece com `--download --yes`. Do GuitarSet (Zenodo 3371780, CC BY 4.0)
  são extraídos apenas os membros do subset, por HTTP range, dentro de `annotation.zip` e
  `audio_mono-mic.zip`, cerca de 29 MB descompactados. Do EGDB (pasta pública do Google Drive dos
  autores) vêm só os arquivos `audio_DI/<n>.wav` e `audio_label/<n>.midi` do subset, cerca de
  19 MB; os ids são resolvidos pela página `embeddedfolderview` da pasta, e se ela mudar dá para
  baixar à mão no mesmo layout.
- Relatórios: `scripts/eval/reports/<dataset>-<subset>.json|.md` (versionáveis, sem áudio), com
  commit (com sufixo `-dirty` se houver alteração rastreada), versão do modelo, tolerâncias, médias
  (macro, por faixa) e números por faixa. O caminho do áudio não fica no relatório; o `data_dir`
  fica.
- Critérios 2 e 3 dependem do download (precisa da permissão do usuário) e ainda não foram rodados.
  O caminho de código foi exercitado com um dataset falso sintético (JAMS/MIDI gerados mais um wav
  senoidal), tanto pelo estimador injetado nos testes quanto pelo Basic Pitch real fora dos testes.
- Técnicas (encaminhado pela REF-TASK-03), conferido só por metadados: o EGDB tem só nota e corda,
  sem rótulo de técnica (README). O Guitar-TECHS (Zenodo 14963133, CC BY 4.0, cerca de 4,1 GB) tem
  categoria "Techniques" com vibrato, harmônicos, bends, palm mute e harmônico artificial (pinch),
  rotulada por arquivo/categoria e com MIDI por corda (Fishman Triple Play), mas não lista
  hammer-on nem pull-off. Por isso a detecção de legato não tem ground truth nesses datasets; bends
  poderiam ser medidos por arquivo no `P*_techniques.zip` (326 MB e 396 MB).

Verificação (2026-10-28, thread principal):

- Download autorizado pelo usuário nesta sessão ("Baixar os dois"), para `~/datasets/tabgen/` (fora do
  repo): `scripts/eval/run.py --dataset guitarset ... --download --yes` → `downloaded 16 file(s)`
  (28,70 MB, Zenodo 3371780, CC BY 4.0); `--dataset egdb ... --download --yes` → `downloaded 16 file(s)`
  (18,96 MB, Google Drive dos autores; EGDB sem licença declarada, só "feel free to use").
- Comando reproduzível (sem download):
  `.venv/bin/python scripts/eval/run.py --dataset guitarset --subset scripts/eval/subsets/guitarset.txt`
  → exit 0, `guitarset/guitarset: 8 tracks, mean note-F1 0.761, mean tab-F1 0.313`.
- `.venv/bin/python scripts/eval/run.py --dataset egdb --subset scripts/eval/subsets/egdb.txt` → exit 0,
  `egdb/egdb: 8 tracks, mean note-F1 0.765, mean tab-F1 0.383` (tab-F1 sobre 5 de 8 faixas; nas faixas
  225, 228 e 234 o mapeamento faixa-MIDI→corda é ambíguo — "ambiguous: N mappings tie" — e o relatório
  marca tab n/a com o motivo).
- Rodar de novo deu os mesmos números (determinístico). Relatórios versionados em
  `scripts/eval/reports/{guitarset-guitarset,egdb-egdb}.{json,md}` (gerados com a árvore suja antes do
  commit: campo `commit` = `bf2d233-dirty`).
- `.venv/bin/pytest -q tests/test_eval_metrics.py` → `15 passed`; `.venv/bin/pytest -q` → `195 passed`;
  `.venv/bin/ruff check .` → `All checks passed!`; `git ls-files | grep -iE "\.(wav|flac|jams)$"` →
  vazio (exit 1).
- Comparação com as referências do plano: nota-F1 0,76 (Basic Pitch ~0,66 em gravação real); tab-F1
  0,31–0,38, bem abaixo do TabCNN ~0,75 no GuitarSet — a atribuição corda/casa é o gargalo (só medido,
  fora do escopo otimizar).

## Execution Log

- **Closed** — commit `d0d38b4` (2026-10-28): feat(eval): add GuitarSet/EGDB evaluation harness with note-F1 and tab-F1
  - Files (`git show --name-status d0d38b4`):
    - `M docs/rite/cycles/refinamento/06-criar-harness-de-avaliacao-em-guitarset-e-egdb.md`
    - `A scripts/eval/__init__.py`
    - `A scripts/eval/download.py`
    - `A scripts/eval/loaders.py`
    - `A scripts/eval/metrics.py`
    - `A scripts/eval/reports/egdb-egdb.json`
    - `A scripts/eval/reports/egdb-egdb.md`
    - `A scripts/eval/reports/guitarset-guitarset.json`
    - `A scripts/eval/reports/guitarset-guitarset.md`
    - `A scripts/eval/run.py`
    - `A scripts/eval/subsets/egdb.txt`
    - `A scripts/eval/subsets/guitarset.txt`
    - `A tests/test_eval_metrics.py`
  - **Files amended** — added to `files`:
    - `scripts/eval/download.py`
    - `scripts/eval/loaders.py`
    - `scripts/eval/reports/egdb-egdb.json`
    - `scripts/eval/reports/egdb-egdb.md`
    - `scripts/eval/reports/guitarset-guitarset.json`
    - `scripts/eval/reports/guitarset-guitarset.md`
- **Reviewed** (2026-10-28) at `ac31695`: FIX-REF-002, FIX-REF-003
