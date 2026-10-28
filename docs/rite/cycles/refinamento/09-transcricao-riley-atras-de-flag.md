---
id: REF-TASK-09
---

# REF-TASK-09 — Transcrição Riley atrás de --transcriber, híbrida com bends do Basic Pitch

## Goal

A CLI ganha `--transcriber basic-pitch|riley`. O stem de guitarra pode ser transcrito pelo modelo
de Riley et al. 2024, avaliado na
[REF-TASK-07](/docs/rite/cycles/refinamento/07-avaliar-modelo-de-transcricao-especifico-de.md)
([decisão](/docs/avaliacao/modelo-guitarra.md)). A saída é híbrida: as notas vêm do Riley e as
curvas de bend vêm do Basic Pitch, para a detecção de técnicas continuar funcionando. O padrão
continua `basic-pitch`. Ele só passa a ser `riley` se o Riley vencer também em stems do Demucs,
medido com o harness.

## Escopo

- In:
  - **Modelo no core, sem o fork.** A definição do CRNN (`Regress_onset_offset_frame_velocity_CRNN`)
    e o pós-processamento por regressão são reescritos em `tabgen/core/transcription/riley.py` a
    partir do projeto MIT de Kong et al. (`qiuqiangkong/piano_transcription`), citando a origem e
    a licença no cabeçalho. O fork `xavriley/piano_transcription_inference` não tem LICENSE e não
    entra no projeto.
  - **Front-end log-mel.** Ou `torchlibrosa` (MIT) como dependência declarada no
    `pyproject.toml`, ou uma reimplementação com librosa/torch. Vale a de menos código, desde que
    tenha equivalência numérica com a original (critério 3).
  - **Pesos.**
    - Origem: `guitar-gaps.pth` de `huggingface.co/xavriley/midi-transcription-models`, por
      `huggingface_hub`.
    - Integridade: revisão fixada e sha256 conferido. É baixado no primeiro uso, como os pesos
      do Demucs, e fica no cache do `huggingface_hub`.
  - **Saída híbrida.**
    - Bends: quando `riley` é escolhido, o Basic Pitch roda no mesmo stem e cada nota do Riley
      recebe os `bends` da nota do Basic Pitch casada (mesmo pitch, onset dentro da tolerância).
      Sem par, `bends=None`.
    - Técnicas: a detecção (`techniques/`) roda sobre o resultado híbrido.
  - **Opção na CLI.**
    - `--transcriber basic-pitch|riley` em `tabgen export` e `tabgen transcribe`, com padrão
      `basic-pitch`.
    - O baixo sempre usa o Basic Pitch.
    - A chave de cache da transcrição e da tablatura inclui o transcritor e o sha dos pesos.
  - **Medição em stems.**
    - O harness ganha `--transcriber` e um modo de mistura: soma do trecho de guitarra com um
      fundo de baixo + bateria sem guitarra, separação pelo Demucs e transcrição do stem
      `guitar`.
    - O fundo é documentado no relatório: a origem do áudio e o comando que o gera.
    - Os relatórios versionados ficam em `scripts/eval/reports/`.
  - **Decisão de padrão.**
    - Regra: o padrão vira `riley` só se, no EGDB misturado, nota-F1 e tab-F1 do `riley` forem
      ambos maiores ou iguais aos do `basic-pitch`. Caso contrário, o padrão fica `basic-pitch`
      e `riley` continua opcional.
    - O resultado e a decisão vão para `docs/avaliacao/modelo-guitarra.md`.
- Out:
  - Modelo de baixo do Riley (`filobass`).
  - Abrir issue de licença no repositório do autor.
  - README e regeneração dos relatórios principais (REF-TASK-08).

## Done criteria

- [x] `grep -rn "piano_transcription_inference" tabgen/ pyproject.toml` vazio; o cabeçalho de
      `tabgen/core/transcription/riley.py` cita `qiuqiangkong/piano_transcription` e MIT;
      `pyproject.toml` declara tudo o que o módulo importa (sem `--target` externo).
- [x] Teste sem rede e sem pesos reais (modelo falso injetado):
  - `riley` produz `NoteEvents` com o `model_version` contendo o sha dos pesos.
  - A fusão híbrida copia `bends` só para notas casadas.
  - Uma nota do Riley com bend casado sai como técnica `bend` no `TabScore`.
  - Esses testes falham contra o HEAD anterior (controle).
- [x] Equivalência com a referência:
  - Comando: `.venv/bin/python scripts/eval/run.py --transcriber riley` nos dois subsets limpos.
  - Resultado: a nota-F1 bate com os relatórios de `scripts/eval/reports/candidates/riley-gaps/`
    (0,892 GuitarSet, 0,860 EGDB) com tolerância de ±0,005, e a diferença fica registrada.
- [x] `.venv/bin/tabgen export <música>.mp3 --transcriber riley -o x.gp5` sai 0 e o `.gp5` relido
      pelo `guitarpro.parse` tem notas na faixa de guitarra. Com `--transcriber basic-pitch` (e sem
      a opção), os testes e goldens existentes não mudam. Probe reproduzível em
      `scripts/probe_e2e_*.py`.
- [x] Tabela basic-pitch vs riley nos subsets misturados (GuitarSet e EGDB), com o comando de cada
      número, em `docs/avaliacao/modelo-guitarra.md`; a decisão de padrão aplicada conforme a regra
      do escopo e registrada nas Notes.
- [x] `.venv/bin/pytest -q` verde, `.venv/bin/ruff check .` limpo, grep de pureza em
      `tabgen/core/` vazio.

## Notes

Criada a pedido do usuário em 2026-10-28, a partir da recomendação da REF-TASK-07.

- **Downloads:** pesos (~99 MB) e o áudio de fundo exigem confirmação do usuário na execução.
- **Equivalência:** a referência numérica (fork + `torchlibrosa`) continua instalada em
  `~/datasets/tabgen/candidates/` e serve para comparar saídas faixa a faixa antes de fechar o
  critério 3.
- **Tempo:** com `riley`, o export roda dois modelos no stem de guitarra (Riley e Basic Pitch). Medir
  o tempo extra e registrar nas Notes.

Execução (2026-10-28), comandos rerodados no thread principal:

- Downloads autorizados pelo usuário nesta sessão: MUSDB18 7s STEMS (Zenodo 3270814, 147 MB,
  cc-by-4.0, sha256 `365f66ac…`) em `~/datasets/tabgen/musdb18-7/`; `guitar-gaps.pth` no cache do
  `huggingface_hub`, revisão `b7bec65a…`, sha256 `65483e7c0e34…`.
- Critério 1: `grep -rn "piano_transcription_inference" tabgen/ pyproject.toml` → vazio (rc=1);
  cabeçalho de `riley.py` cita `qiuqiangkong/piano_transcription (MIT License …)`; `pyproject.toml`
  ganhou `numpy`, `torchlibrosa==0.1.0`, `huggingface_hub`.
- Critério 2: `.venv/bin/pytest -q tests/test_riley_transcription.py` → `8 passed`. Controle: o mesmo
  arquivo num worktree do HEAD (`f5214b8`) → `ImportError: cannot import name 'riley' from
  'tabgen.core.transcription'`.
- Critério 3: `.venv/bin/python scripts/eval/run.py --dataset <d> --subset scripts/eval/subsets/<d>.txt
  --transcriber riley` → `guitarset: mean note-F1 0.892, mean tab-F1 0.453`, `egdb: mean note-F1
  0.860, mean tab-F1 0.486`; diferença 0,000 para `reports/candidates/riley-gaps/` (worker: todas
  as faixas idênticas; ativações iguais ao fork numa faixa).
- Critério 4: `.venv/bin/tabgen export "You and I.flac" --transcriber riley -o …/youandi-riley.gp5`
  → rc=0; `guitarpro.parse` → `{'guitar': 994, 'bass': 896}`. `scripts/probe_e2e_riley.py` → `PASS …
  basic-pitch 1.8 s, riley 4.5 s, extra +2.7 s. Default export (no option) hit the riley cache
  entry`. `scripts/probe_e2e_export.py` → `PASS` (fixado em `--transcriber basic-pitch`: no seno puro
  o Riley não acha nota de guitarra). Tempo na música real (worker, separação em cache): basic-pitch
  9,1 s, riley 16,6 s.
- Critério 5: `.venv/bin/python scripts/eval/run.py --dataset <d> --subset … --mix --transcriber <t>`
  → basic-pitch GuitarSet 0.745/0.334, EGDB 0.615/0.224; riley GuitarSet 0.879/0.472, EGDB
  0.691/0.336. Regra aplicada: riley ≥ basic-pitch nas duas métricas do EGDB misturado, então
  `DEFAULT_TRANSCRIBER = "riley"`.
- Critério 6: `.venv/bin/pytest -q` → `221 passed`; `ruff check .` → `All checks passed!`; grep de
  pureza vazio.
- Desvios registrados: tag de cache da tablatura curta (`+riley-<sha8>-<hash6>`) porque o nome do
  arquivo passava de 255 bytes (253 bytes com gtype electric, perto do limite); `torch.load` com
  `weights_only=False` só depois do sha256 conferir. Variação de Demucs (`shifts` aleatório): duas
  separações frias da mesma música deram 994 e 1040 notas de guitarra.

## Execution Log

- **Closed** — commit `a54eeaf` (2026-10-28): feat(transcription): add hybrid Riley guitar transcriber behind --transcriber and make it the default
  - Files (`git show --name-status a54eeaf`):
    - `M docs/avaliacao/modelo-guitarra.md`
    - `M docs/rite/cycles/refinamento/08-fechar-fase-4.md`
    - `M docs/rite/cycles/refinamento/09-transcricao-riley-atras-de-flag.md`
    - `M docs/rite/cycles/refinamento/progress.json`
    - `M docs/rite/cycles/refinamento/progress.md`
    - `M pyproject.toml`
    - `A scripts/eval/mix.py`
    - `A scripts/eval/reports/mixed/basic-pitch/egdb-egdb.json`
    - `A scripts/eval/reports/mixed/basic-pitch/egdb-egdb.md`
    - `A scripts/eval/reports/mixed/basic-pitch/guitarset-guitarset.json`
    - `A scripts/eval/reports/mixed/basic-pitch/guitarset-guitarset.md`
    - `A scripts/eval/reports/mixed/riley/egdb-egdb.json`
    - `A scripts/eval/reports/mixed/riley/egdb-egdb.md`
    - `A scripts/eval/reports/mixed/riley/guitarset-guitarset.json`
    - `A scripts/eval/reports/mixed/riley/guitarset-guitarset.md`
    - `A scripts/eval/reports/riley/egdb-egdb.json`
    - `A scripts/eval/reports/riley/egdb-egdb.md`
    - `A scripts/eval/reports/riley/guitarset-guitarset.json`
    - `A scripts/eval/reports/riley/guitarset-guitarset.md`
    - `M scripts/eval/run.py`
    - `M scripts/probe_e2e_export.py`
    - `A scripts/probe_e2e_riley.py`
    - `M tabgen/cli/main.py`
    - `M tabgen/core/pipeline.py`
    - `M tabgen/core/transcription/__init__.py`
    - `A tabgen/core/transcription/riley.py`
    - `A tests/test_riley_transcription.py`
- **Reviewed** (2026-10-28) at `dee893a`: no finding
