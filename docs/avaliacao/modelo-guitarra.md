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
