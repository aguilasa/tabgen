# Avaliação: modelo de transcrição específico de guitarra (estágio 4)

Decisão pedida pela [REF-TASK-07](/docs/rite/cycles/refinamento/07-avaliar-modelo-de-transcricao-especifico-de.md):
trocar ou não o Basic Pitch por um modelo treinado só para guitarra
([plano, Estágio 4](/docs/planejamento/audio-para-tablatura.md#estágio-4--transcrição-áudio--notas-o-coração)).
A troca em si não faz parte desta tarefa: a decisão é do usuário.

## Disponibilidade e licenças (verificado em 2026-10-28)

| Candidato | Código | Pesos | Licença | Situação |
|---|---|---|---|---|
| Riley, Edwards & Dixon 2024, "High Resolution Guitar Transcription via Domain Adaptation" ([arXiv 2402.15258](https://arxiv.org/abs/2402.15258), ICASSP 2024) | [xavriley/hf_midi_transcription](https://github.com/xavriley/hf_midi_transcription) (wrapper) + [xavriley/piano_transcription_inference](https://github.com/xavriley/piano_transcription_inference) (fork da inferência de Kong et al.) | [`guitar-fl.pth`](https://huggingface.co/xavriley/midi-transcription-models) (98,9 MB, sha256 `50d93dba89bd…`) | Pesos e wrapper: MIT (model card do HF e `pyproject.toml`). O fork da inferência **não tem arquivo LICENSE**, nem o original `qiuqiangkong/piano_transcription_inference`; o projeto de treino `qiuqiangkong/piano_transcription` é MIT; `torchlibrosa` é MIT | **Disponível; avaliado** |
| Riley et al. 2024, GAPS ([arXiv 2408.08653](https://arxiv.org/abs/2408.08653), ISMIR 2024): mesma arquitetura, treinada no dataset GAPS | Mesmo código | [`guitar-gaps.pth`](https://huggingface.co/xavriley/midi-transcription-models) (99,2 MB, sha256 `65483e7c0e34…`). É o default de `guitar` no `instruments.json` do wrapper | Mesma | **Disponível; avaliado** |
| TART, Gupta et al. 2025 ([arXiv 2510.02597](https://arxiv.org/abs/2510.02597)) | Nenhum link de código na página do arXiv nem no HTML do artigo | Nenhum | — | Indisponível |
| YourMT3+ ([arXiv 2407.04822](https://arxiv.org/abs/2407.04822)), como controle | [mimbres/YourMT3](https://github.com/mimbres/YourMT3) | Checkpoints no Space [mimbres/YourMT3](https://huggingface.co/spaces/mimbres/YourMT3) (card apache-2.0) | Código GPL-3.0 | Disponível, **não rodado**: GuitarSet está no treino (números contaminados no subset), modelo pesado e, segundo o plano, pior que o Basic Pitch em gravação real |

Como foi verificado: API do GitHub (`/repos/<repo>` e `/repos/<repo>/license`), API do Hugging
Face (`/api/models?author=xavriley`, `/api/models/xavriley/midi-transcription-models/tree/main`,
`/api/spaces/mimbres/YourMT3`), páginas do arXiv e a página do projeto
<https://xavriley.github.io/HighResolutionGuitarTranscription/>. Os sha256 dos arquivos baixados
batem com os OIDs LFS publicados no HF.

Licença no critério do plano: non-commercial é aceito e AGPL é evitada. Riley (MIT) passa. A falta
de LICENSE no código de inferência fica como pendência de uma eventual integração: ou se pede a
licença ao autor, ou a definição do modelo é reescrita a partir do projeto MIT de Kong et al.

## Comparação no subset do harness

Mesmo subset da [REF-TASK-06](/docs/rite/cycles/refinamento/06-criar-harness-de-avaliacao-em-guitarset-e-egdb.md)
(8 trechos GuitarSet mono-mic, 8 clipes EGDB DI), mesma métrica (onset ±50 ms, pitch ±50 cents,
sem critério de offset) e o mesmo fretting DP (`guitar_config()`, afinação padrão). Só a
transcrição muda. O Basic Pitch foi rodado de novo no mesmo commit para a linha de base.

| Modelo | GuitarSet nota-F1 | GuitarSet tab-F1 | EGDB nota-F1 | EGDB tab-F1 (5 de 8 faixas) |
|---|---|---|---|---|
| Basic Pitch (atual) | 0,761 | 0,341 | 0,765 | 0,418 |
| Riley `guitar-fl` | **0,925** | **0,468** | 0,843 | 0,429 |
| Riley `guitar-gaps` | 0,892 | 0,453 | **0,860** | **0,486** |

Precisão / revocação de nota: Basic Pitch 0,732/0,815 (GuitarSet) e 0,687/0,877 (EGDB);
`guitar-fl` 0,919/0,931 e 0,812/0,884; `guitar-gaps` 0,886/0,902 e 0,872/0,855. O ganho do
Basic Pitch para os candidatos vem sobretudo da precisão (menos notas falsas).

Comando que gera cada número (a partir da raiz, com os pesos em
`~/datasets/tabgen/candidates/weights/` e a inferência instalada com
`pip install --no-deps --target ~/datasets/tabgen/candidates/site git+https://github.com/xavriley/piano_transcription_inference.git torchlibrosa`):

```bash
for c in basic-pitch riley-fl riley-gaps; do
  for d in guitarset egdb; do
    .venv/bin/python scripts/eval/candidates.py --candidate $c --dataset $d \
      --subset scripts/eval/subsets/$d.txt
  done
done
```

Relatórios por faixa em [scripts/eval/reports/candidates/](/scripts/eval/reports/candidates/)
(`<candidato>/<dataset>-<subset>.md|.json`). Eles registram o commit `7628659-dirty`: o código
era o desse commit e o "dirty" vinha só da marcação de progresso do Rite
(`docs/rite/cycles/refinamento/progress.*`). Tempo: cada execução dos candidatos levou ~9 s na
RTX 3060 Laptop (8 faixas, modelo carregado uma vez por execução); Basic Pitch ~1 s com cache
quente.

## Ressalvas

- **Contaminação:** o artigo do `guitar-fl` afirma GuitarSet zero-shot. O artigo do GAPS reporta
  GuitarSet "supervised e zero-shot", e não foi possível confirmar qual das variantes é o
  `guitar-gaps.pth`. Por isso o número dele no GuitarSet pode estar inflado. EGDB não aparece no
  treino de nenhum dos dois e é a comparação mais limpa.
- **Áudio limpo:** os dois subsets são guitarra isolada (microfone mono, DI). No tabgen a entrada
  é um stem do Demucs, com vazamento e artefatos; o ganho em música mixada não foi medido. Os
  modelos Riley foram treinados para guitarra solo.
- **Bends:** os modelos Riley não produzem curva de pitch bend. A detecção de bends e slides
  ([REF-TASK-02](/docs/rite/cycles/refinamento/02-detectar-bends-e-slides-a-partir-dos-pitch-bends.md))
  depende de `Note.bends`, que vem do Basic Pitch. Trocar o modelo perde essa entrada, a menos que
  as duas saídas sejam combinadas (notas do Riley, bends do Basic Pitch).
- **Baixo:** fora do escopo. O HF tem `filobass_20000_iterations.pth` (baixo), não avaliado.
- **Tab-F1** sobe menos que nota-F1 porque o fretting DP é o mesmo. O viés de cordas graves
  descrito na REF-TASK-05 segue limitando o tab-F1.

## Recomendação

**Adotar o Riley como transcrição do stem de guitarra, numa tarefa nova, com `guitar-gaps` como
padrão.** O `guitar-gaps` lidera no EGDB, a comparação sem contaminação: +9,5 pontos de nota-F1 e
+6,8 de tab-F1 sobre o Basic Pitch. O `guitar-fl` lidera no GuitarSet (+16,4 e +12,7), mas fica
quase empatado em tab-F1 no EGDB. Os dois superam o Basic Pitch em todas as colunas.

A tarefa nova precisa cobrir:

1. Medir em stems do Demucs de músicas reais antes de trocar o padrão. Se o ganho sumir no áudio
   separado, manter o Basic Pitch.
2. Manter o Basic Pitch para os bends (saída híbrida) ou para o baixo, conforme a medição.
3. Resolver a licença do código de inferência (pedir ao autor ou reescrever o modelo a partir do
   projeto MIT de Kong et al.).
4. Tratar o download dos pesos (~99 MB) e a dependência `torchlibrosa`.

Se essas condições não forem atendidas, a recomendação é manter o Basic Pitch.

## Integração e medição em stems do Demucs (REF-TASK-09)

O Riley entrou no core atrás de `--transcriber basic-pitch|riley`
([REF-TASK-09](/docs/rite/cycles/refinamento/09-transcricao-riley-atras-de-flag.md)), em
`tabgen/core/transcription/riley.py`:

- **Código:** a CRNN e o pós-processamento por regressão foram reescritos a partir do projeto MIT
  de Kong et al. (`qiuqiangkong/piano_transcription`). O fork sem LICENSE não entra no projeto. O
  front-end log-mel é o `torchlibrosa==0.1.0` (MIT), declarado no `pyproject.toml` junto com
  `huggingface_hub` e `numpy`. É menos código que reimplementar, e as chaves do state-dict do
  checkpoint casam sem adaptação (carga com `strict=True`).
- **Pesos:** `guitar-gaps.pth` de `xavriley/midi-transcription-models`, revisão
  `b7bec65a2b860aca72856b0feef58b5df407b777`, sha256 `65483e7c0e34…` conferido antes da carga.
  São baixados no primeiro uso para o cache do `huggingface_hub`.
- **Saída híbrida:** as notas vêm do Riley. O Basic Pitch roda no mesmo stem, e cada nota do
  Riley recebe os `bends` da nota do Basic Pitch de mesmo pitch com onset a até 50 ms
  (`BEND_MATCH_TOLERANCE_S`, a tolerância de onset do harness). O casamento é um-para-um, pelo
  onset mais próximo. Sem par, `bends=None`. A detecção de técnicas roda sobre esse resultado.
  O baixo usa sempre o Basic Pitch.
- **Cache:** a transcrição híbrida tem versão própria, com o sha dos pesos, a versão do Basic
  Pitch e a tolerância. A chave da tablatura ganha `+riley-<sha>-<digest>` só com `riley`. As
  chaves do `basic-pitch` não mudaram.

### Equivalência com a referência (áudio limpo)

Com o mesmo subset e a mesma métrica, a implementação do core reproduz exatamente os relatórios
da referência (fork + `torchlibrosa`) em
[candidates/riley-gaps/](/scripts/eval/reports/candidates/riley-gaps/). As saídas por frame das
quatro cabeças têm diferença máxima 0,0 numa faixa do GuitarSet. Nas 16 faixas, nota-F1,
tab-F1 e contagens de notas são iguais faixa a faixa:

| Subset | nota-F1 referência | nota-F1 core | tab-F1 referência | tab-F1 core |
|---|---|---|---|---|
| GuitarSet | 0,892 | 0,892 | 0,453 | 0,453 |
| EGDB | 0,860 | 0,860 | 0,486 | 0,486 |

```bash
for d in guitarset egdb; do
  .venv/bin/python scripts/eval/run.py --dataset $d --subset scripts/eval/subsets/$d.txt \
    --transcriber riley          # relatórios em scripts/eval/reports/riley/
done
```

### Medição em stems (modo de mistura do harness)

O modo `--mix` do harness ([scripts/eval/mix.py](/scripts/eval/mix.py)) reproduz a entrada real
do tabgen:

- **Fundo:** bateria + baixo de uma faixa do MUSDB18. São os trechos de 7 s do MUSDB18
  (Zenodo, registro 3270814, `MUSDB18-7-STEMS.zip`, CC BY 4.0), só das 50 faixas de `test/`,
  que ficaram fora do treino do Demucs. Streams do `.stem.mp4`: 0 mix, 1 bateria, 2 baixo,
  3 other, 4 vocais. A ordem foi conferida numa faixa: a soma de 1 a 4 reconstrói o stream 0
  com resíduo de 6 % do RMS (codificação AAC), e o stream 2 tem o centroide espectral mais grave.
- **Escolha do fundo:** para o trecho na posição `i` do subset, a faixa
  `sorted(test/*.stem.mp4)[i % 50]`.
- **Mistura:** o fundo é repetido em loop até a duração do trecho e posto no mesmo RMS da
  guitarra (`GUITAR_TO_BACKING_DB = 0`). Se o pico passar de 0,99, a mistura inteira é
  atenuada.
- **Separação e transcrição:** o Demucs do tabgen (`htdemucs_ft+htdemucs_6s`) separa a mistura,
  e o stem `guitar` vai para o transcritor. Depois vêm o mesmo fretting e as mesmas métricas.
- **Arquivos:** misturas, stems e caches ficam fora do repositório, em `~/datasets/tabgen/mixed/`.
  Cada relatório registra o fundo de cada trecho e o comando que o gerou.

| Transcritor | GuitarSet misturado nota-F1 | GuitarSet misturado tab-F1 | EGDB misturado nota-F1 | EGDB misturado tab-F1 (5 de 8 faixas) |
|---|---|---|---|---|
| `basic-pitch` | 0,745 | 0,334 | 0,615 | 0,224 |
| `riley` | **0,879** | **0,472** | **0,691** | **0,336** |

Precisão / revocação de nota: `basic-pitch` 0,736/0,771 (GuitarSet) e 0,598/0,662 (EGDB);
`riley` 0,896/0,866 e 0,772/0,647.

Comando de cada número (a partir da raiz). Os relatórios ficam em
[scripts/eval/reports/mixed/](/scripts/eval/reports/mixed/) (`<transcritor>/<dataset>-<subset>.md|.json`):

```bash
for t in basic-pitch riley; do
  for d in guitarset egdb; do
    .venv/bin/python scripts/eval/run.py --dataset $d --subset scripts/eval/subsets/$d.txt \
      --mix --transcriber $t
  done
done
```

Ressalvas da medição:

- **Queda no EGDB:** os dois transcritores perdem mais no EGDB (DI de guitarra elétrica) que no
  GuitarSet. Na faixa 216 o stem `guitar` sai quase vazio (RMS 0,009 contra 0,092 da guitarra
  original). O Demucs mandou a guitarra para outro stem, e os dois transcritores ficam perto de
  zero nessa faixa.
- **Reprodutibilidade a frio:** o Demucs aplica um deslocamento aleatório (`shifts`). Uma
  separação refeita do zero pode variar um pouco. Os números acima saem dos stems em cache.

### Decisão de padrão

Regra da tarefa: o padrão vira `riley` só se, no EGDB misturado, nota-F1 e tab-F1 do `riley`
forem ambos maiores ou iguais aos do `basic-pitch`. Resultado: nota-F1 0,691 ≥ 0,615 e tab-F1
0,336 ≥ 0,224. **O padrão passa a ser `riley`** (`DEFAULT_TRANSCRIBER` em
`tabgen/core/pipeline.py`, usado por `tabgen export` e `tabgen transcribe`). O
`--transcriber basic-pitch` continua disponível. O harness mantém `basic-pitch` como padrão, para
que os relatórios principais (`scripts/eval/reports/<dataset>-<subset>.*`) continuem a ser os da
linha de base.

Tempo extra (export de "You and I", 248 s, RTX 3060 Laptop, separação e análise em cache,
caches de transcrição e tablatura limpos): `basic-pitch` 9,1 s e `riley` 16,6 s, ou seja +7,5 s.
O tempo extra vem do modelo Riley, que inclui a importação do torch e a carga dos pesos, e do
Basic Pitch rodado de novo para os bends. No trecho sintético de 10 s de
`scripts/probe_e2e_riley.py` são 1,9 s contra 4,5 s.
