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

- [ ] `grep -rn "piano_transcription_inference" tabgen/ pyproject.toml` vazio; o cabeçalho de
      `tabgen/core/transcription/riley.py` cita `qiuqiangkong/piano_transcription` e MIT;
      `pyproject.toml` declara tudo o que o módulo importa (sem `--target` externo).
- [ ] Teste sem rede e sem pesos reais (modelo falso injetado):
  - `riley` produz `NoteEvents` com o `model_version` contendo o sha dos pesos.
  - A fusão híbrida copia `bends` só para notas casadas.
  - Uma nota do Riley com bend casado sai como técnica `bend` no `TabScore`.
  - Esses testes falham contra o HEAD anterior (controle).
- [ ] Equivalência com a referência:
  - Comando: `.venv/bin/python scripts/eval/run.py --transcriber riley` nos dois subsets limpos.
  - Resultado: a nota-F1 bate com os relatórios de `scripts/eval/reports/candidates/riley-gaps/`
    (0,892 GuitarSet, 0,860 EGDB) com tolerância de ±0,005, e a diferença fica registrada.
- [ ] `.venv/bin/tabgen export <música>.mp3 --transcriber riley -o x.gp5` sai 0 e o `.gp5` relido
      pelo `guitarpro.parse` tem notas na faixa de guitarra. Com `--transcriber basic-pitch` (e sem
      a opção), os testes e goldens existentes não mudam. Probe reproduzível em
      `scripts/probe_e2e_*.py`.
- [ ] Tabela basic-pitch vs riley nos subsets misturados (GuitarSet e EGDB), com o comando de cada
      número, em `docs/avaliacao/modelo-guitarra.md`; a decisão de padrão aplicada conforme a regra
      do escopo e registrada nas Notes.
- [ ] `.venv/bin/pytest -q` verde, `.venv/bin/ruff check .` limpo, grep de pureza em
      `tabgen/core/` vazio.

## Notes

Criada a pedido do usuário em 2026-10-28, a partir da recomendação da REF-TASK-07.

- **Downloads:** pesos (~99 MB) e o áudio de fundo exigem confirmação do usuário na execução.
- **Equivalência:** a referência numérica (fork + `torchlibrosa`) continua instalada em
  `~/datasets/tabgen/candidates/` e serve para comparar saídas faixa a faixa antes de fechar o
  critério 3.
- **Tempo:** com `riley`, o export roda dois modelos no stem de guitarra (Riley e Basic Pitch). Medir
  o tempo extra e registrar nas Notes.

## Execution Log
