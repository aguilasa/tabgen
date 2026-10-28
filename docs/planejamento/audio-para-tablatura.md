# Áudio → Tablatura: estudo e planejamento

> Ferramenta open source que recebe o áudio de uma música, separa os instrumentos
> (guitarra, violão, baixo), identifica tom e acordes, e gera tablatura nos formatos
> Guitar Pro (.gp5), TuxGuitar e outros — usando apenas ferramentas e modelos gratuitos.
>
> Estudo feito em 2026-10-25. Nome de trabalho: **tabgen**.

---

## 1. Visão geral

### O que a ferramenta faz (v1, CLI)

```bash
tabgen musica.mp3 -o musica.gp5
# ou por etapas:
tabgen separar musica.mp3        # gera stems (guitarra, baixo, bateria, vocal...)
tabgen analisar musica.mp3       # tom, acordes, andamento, compassos
tabgen transcrever stems/        # MIDI por instrumento
tabgen exportar --formato gp5    # tablatura final
```

### É viável?

**Sim, com expectativas calibradas.** Cada estágio do problema tem solução open
source madura ou pesquisa recente com código:

| Capacidade | Estado da arte open source | Maturidade |
|---|---|---|
| Separar instrumentos | Demucs v4 / BS-RoFormer | ★★★★★ madura |
| Detectar tom e acordes | madmom / Essentia | ★★★★☆ madura |
| Detectar andamento/compassos | madmom / Beat This! | ★★★★☆ madura |
| Áudio → notas (MIDI) | Basic Pitch / MT3 | ★★★☆☆ boa, com erros |
| Notas → corda/casa (tab) | TabCNN / TART / heurísticas | ★★☆☆☆ pesquisa ativa |
| Escrever .gp5 | PyGuitarPro | ★★★★☆ madura |

O elo fraco é a transcrição automática (precisão ~66% em gravações reais de
guitarra) e a atribuição corda/casa. O resultado será sempre um **rascunho bom
para revisão manual**, não uma tablatura perfeita — e isso já é o estado da arte
mesmo em ferramentas comerciais pagas.

### Linguagem

**Python 3.10+.** Todo o ecossistema MIR (Music Information Retrieval) relevante é
Python/PyTorch: Demucs, Basic Pitch, madmom, librosa, music21, PyGuitarPro.
Qualquer outra linguagem obrigaria a reimplementar ou embrulhar esses projetos.

---

## 2. Arquitetura em camadas (core separado das interfaces)

Requisito do projeto: **CLI na v1, mas pronto para evoluir para web ou desktop.**
O pipeline inteiro vive numa biblioteca pura (`core`); as interfaces são camadas
finas que consomem a mesma API.

```
tabgen/
├── core/                  # biblioteca pura — nenhum print(), nenhum HTTP
│   ├── separation/        # estágio 1: Demucs
│   ├── analysis/          # estágios 2–3: tom, acordes, beats/compassos
│   ├── transcription/     # estágio 4: Basic Pitch → notas
│   ├── fretting/          # estágio 5: atribuição corda/casa
│   ├── export/            # estágio 6: gp5, MusicXML, MIDI, ASCII
│   ├── models.py          # dataclasses compartilhadas (contratos entre estágios)
│   └── pipeline.py        # orquestra os estágios, emite eventos de progresso
├── cli/                   # camada fina: typer + rich (barra de progresso)
├── web/       (futuro)    # FastAPI + fila de jobs (Celery/RQ), reusa core
└── desktop/   (futuro)    # Tauri ou PySide, reusa core
```

Regras de dependência:

1. **`core` não conhece terminal, HTTP nem GUI.** Progresso e logs saem por
   callbacks/eventos (`on_progress(stage, pct)`), nunca por `print()`.
2. **Contratos entre estágios são dataclasses serializáveis em JSON**
   (`SeparationResult`, `AnalysisResult`, `NoteEvents`, `TabScore`). Isso permite:
   - rodar cada estágio como job separado na futura versão web (a separação leva
     minutos; numa web app vira job assíncrono com fila);
   - cachear resultados intermediários em disco (`.tabgen/` ao lado do áudio) e
     re-executar só o estágio que mudou;
   - testar cada estágio isoladamente com fixtures.
3. **CLI é só um consumidor**: parseia argumentos, chama `core.pipeline`, desenha
   progresso. Se a CLI tiver qualquer lógica musical, está no lugar errado.
4. Modelos de ML são carregados sob demanda (lazy) e o caminho dos pesos é
   configurável — na web, os workers carregam uma vez e atendem vários jobs.

---

## 3. O pipeline em 6 estágios

```
áudio (mp3/wav/flac)
   │  ffmpeg → wav 44.1 kHz estéreo
   ▼
┌─────────────────────────────────────────────────────┐
│ 1. SEPARAÇÃO DE FONTES (Demucs)                     │
│    mix → vocais, bateria, baixo, guitarra, "outros" │
└─────────────────────────────────────────────────────┘
   ▼
┌─────────────────────────────────────────────────────┐
│ 2. TOM + ACORDES (madmom, sobre mix sem bateria)    │
│ 3. BEATS/DOWNBEATS → andamento e grade de compassos │
└─────────────────────────────────────────────────────┘
   ▼
┌─────────────────────────────────────────────────────┐
│ 4. TRANSCRIÇÃO áudio→notas por stem (Basic Pitch)   │
│    notas com início, duração, pitch, bends          │
└─────────────────────────────────────────────────────┘
   ▼
┌─────────────────────────────────────────────────────┐
│ 5. ATRIBUIÇÃO CORDA/CASA (programação dinâmica)     │
│    cada nota → (corda, casa) minimizando custo de   │
│    digitação; afinação configurável                  │
└─────────────────────────────────────────────────────┘
   ▼
┌─────────────────────────────────────────────────────┐
│ 6. QUANTIZAÇÃO + EXPORTAÇÃO                         │
│    notas na grade de compassos → .gp5, MusicXML,    │
│    MIDI, tab ASCII                                   │
└─────────────────────────────────────────────────────┘
```

### Estágio 1 — Separação de fontes

**Escolha: [Demucs v4 (htdemucs)](https://github.com/adefossez/demucs)** — modelo
híbrido transformer, roda bem em GPU NVIDIA.

- `htdemucs_ft` (fine-tuned): melhor qualidade, 4 stems (vocais, bateria, baixo,
  outros). ~4× mais lento que o normal, irrelevante com GPU.
- `htdemucs_6s`: 6 stems, **inclui stem de guitarra e piano** — qualidade do stem
  de guitarra é mediana, mas é o único caminho direto para isolar guitarra.
  Estratégia: usar os dois — `htdemucs_ft` para baixo (excelente, SDR ~12) e
  `htdemucs_6s` para o stem de guitarra; o violão costuma cair em "outros"/guitar.
- Atenção: o [repo original (facebookresearch) foi arquivado em jan/2025](https://arxiv.org/pdf/2607.23395);
  o fork ativo é o do autor, `adefossez/demucs`. Instalável via pip.

Alternativas/upgrades futuros:
- **BS-RoFormer / Mel-Band RoFormer** — estado da arte para vocais/instrumental
  ([benchmarks do MVSEP](https://mvsep.com/en/algorithms)); pesos comunitários no
  projeto [Music-Source-Separation-Training](https://arxiv.org/pdf/2607.23395).
- **MDX23** ([lucataco/mvsep-mdx23](https://replicate.com/lucataco/mvsep-mdx23-music-separation)) —
  ensemble Demucs4 + MDX, ligeiramente melhor que htdemucs em baixo/bateria.
- **Spleeter** (Deezer): mais rápido, qualidade inferior — [não vale mais a pena](https://stemsplit.io/blog/spleeter-vs-demucs.md).

### Estágios 2–3 — Tom, acordes, beats e compassos

**Escolha: [madmom](https://pypi.org/project/madmom/)** (BSD; modelos CC BY-NC-SA — ok
para projeto não comercial):

- **Acordes**: `madmom.features.chords.CNNChordFeatureProcessor` +
  `CRFChordRecognitionProcessor` — reconhecimento maior/menor por frame, com
  timestamps. Rodar sobre a soma dos stems harmônicos (mix − bateria) melhora o resultado.
- **Tom**: `madmom.features.key` (key detection CNN, [disponível desde a v0.16](https://data.safetycli.com/changelogs/madmom)).
  Validar cruzando com o histograma de notas transcritas no estágio 4.
- **Beats/downbeats**: `DBNDownBeatTracker` ([Böck, Krebs & Widmer, ISMIR 2016](https://madmom.readthedocs.io/en/v0.16/modules/features/downbeats.html)) —
  dá BPM, posição de cada beat e dos downbeats → grade de compassos para a quantização.

Alternativas:
- **[Beat This!](https://arxiv.org/pdf/2407.21658)** (ISMIR 2024, grupo do Widmer) —
  beat tracker sem DBN, lida com mudanças de fórmula de compasso e rubato; melhor
  F1 publicado. Usar se o madmom engasgar em músicas com mudança de compasso.
- **[Essentia](https://github.com/ivorforce/essentia)** (AGPL) — tem key/chord detection;
  AGPL contamina o projeto, usar só se o madmom decepcionar.
- **Chordino (Vamp plugin)** — clássico, qualidade inferior aos modelos neurais.
- madmom é Cython e historicamente demora a suportar Python novo — testar a
  instalação logo na fase 2; se travar, há forks da comunidade com wheels atualizadas.

### Estágio 4 — Transcrição áudio → notas (o coração)

**Escolha: [Basic Pitch](https://github.com/spotify/basic-pitch)** (Spotify, Apache 2.0):

- Leve (roda até em navegador), instrumento-agnóstico, polifônico.
- **Detecta pitch bends** — essencial para notar bends e slides de guitarra depois.
- Em [teste com gravações comerciais reais de guitarra](https://arxiv.org/pdf/2402.15258),
  F-measure de nota **66.1 vs 52.4 do MT3** pré-treinado. É a melhor opção
  genérica pronta para uso.
- Saída: lista de notas (onset, offset, pitch MIDI, confiança, bends) — mapeia
  direto para o contrato `NoteEvents` do core.

Pontos de atenção e alternativas:
- **Baixo**: transcrever o stem de baixo separadamente com Basic Pitch configurado
  para faixa grave; o [MT3 pré-treinado transcreve baixo uma oitava acima](https://arxiv.org/pdf/2407.04822)
  (bug conhecido) — mais um motivo para Basic Pitch. Aplicar verificação de oitava
  contra o espectro do stem.
- **[MT3](https://arxiv.org/pdf/2111.03017) / [YourMT3+](https://arxiv.org/pdf/2407.04822)** —
  transformer multi-instrumento, números fortes em benchmark próprio
  (GuitarSet frame-F1 0.89) mas pior que Basic Pitch em gravação real; pesado. Opção de upgrade.
- **Transcrição específica de guitarra por adaptação de domínio**
  ([Riley et al. 2024](https://arxiv.org/pdf/2402.15258)): F-measure 84.7 em
  gravações reais — muito acima de ambos. Pesos públicos (MIT) verificados em 2026-10-28;
  desde a Fase 4 é o transcritor padrão do stem de guitarra (`--transcriber riley`, com bends do
  Basic Pitch). Ver [avaliação](/docs/avaliacao/modelo-guitarra.md).

### Estágio 5 — Atribuição corda/casa (o problema difícil)

Uma nota MIDI (ex.: E4) tem até 6 posições possíveis no braço. Tablatura boa
minimiza deslocamento de mão, respeita digitação de acordes e prefere posições
idiomáticas. **Não existe lib pronta madura** — é onde o projeto cria valor próprio.

Abordagem v1 — **programação dinâmica sobre heurísticas** (sem ML):

- Estado = posição da mão (casa ~atual); custo = deslocamento + abertura de dedos
  + penalidade por cordas soltas fora de contexto + bônus por manter forma de acorde
  (usar os acordes do estágio 2 como prior: se o acorde é Am, preferir as formas de Am).
- Afinação e nº de cordas configuráveis (guitarra 6, baixo 4/5, violão, drop D...).
- Referências de código: [tuttut](https://pypi.org/project/tuttut/) (qualquer
  afinação/nº de cordas, MIT) e [tayuya](https://pypi.org/project/tayuya) (MIT,
  só solos em afinação padrão) — ambos convertem MIDI → tab com heurísticas simples; ler o código, não depender deles.

Caminho de pesquisa (v2+), ML estimando corda/casa direto do áudio
(timbre de cada corda difere):

- **TabCNN** ([Wiggins & Kim, ISMIR 2019](https://arxiv.org/pdf/2204.08094)) — CNN
  que emite 6 distribuições (uma por corda) sobre 21 casas, por frame. Tablature-F1
  ~0.75 e [TDR ~0.90 no GuitarSet](https://dafx.de/paper-archive/2024/papers/DAFx24_paper_99.pdf).
  Implementação de referência no [amt-tools (cwitkowitz)](https://github.com/cwitkowitz/guitar-transcription-with-inhibition).
- **TART** ([Berkeley, 2025/2026](https://arxiv.org/pdf/2510.02597)) — pipeline
  completo technique-aware (áudio→MIDI, classificador de técnicas, transformer
  corda/casa, gerador de tab). Tab-F1 fim-a-fim ~54% zero-shot — mostra o teto
  atual. Código ainda não confirmado público; acompanhar.

### Estágio 6 — Quantização e exportação

1. **Quantizar**: projetar onsets/offsets das notas na grade de beats do estágio 3
   (semicolcheia como resolução padrão; tercinas detectadas por ajuste). Essa etapa
   define se a tab "parece certa" — merece testes dedicados.
2. **Montar partitura simbólica**: [music21](https://www.music21.org) (BSD) para
   estrutura de compassos, armaduras (tom do estágio 2), símbolos de acorde e export MusicXML.
3. **Escrever .gp5**: [PyGuitarPro](https://github.com/Perlence/PyGuitarPro)
   (LGPL, port do alphaTab/TuxGuitar) — lê e **escreve GP3/GP4/GP5**, com modelo de
   objetos completo (Song → Track → Measure → Voice → Beat → Note, com corda, casa,
   efeitos como bend/slide/hammer-on). Não suporta GPX/GP6+ — irrelevante, pois
   .gp5 abre no Guitar Pro 6/7/8 e no TuxGuitar.

Compatibilidade de formatos:

| Formato | Gerado por | Guitar Pro lê? | TuxGuitar lê? |
|---|---|---|---|
| **.gp5** | PyGuitarPro | ✅ | ✅ ([importa GP3–GP5, GPX, PTB, TEF, MIDI](https://fileinfo.com/software/tuxguitar/tuxguitar)) |
| MusicXML | music21 | ✅ | ⚠️ exporta, import não confirmado |
| MIDI | mido/pretty_midi | ✅ (sem corda/casa) | ✅ (sem corda/casa) |
| Tab ASCII | próprio | — | — |

**.gp5 é o formato-alvo**: único que carrega corda/casa + técnicas e abre nos dois
programas. MusicXML e MIDI como secundários.

---

## 4. Licenças (tudo gratuito, projeto não comercial)

| Componente | Licença | Observação |
|---|---|---|
| Demucs (código) | MIT | pesos: [tag MIT no HF, mas há relato de "research-only"](https://huggingface.co/adefossez/HTDemucs/discussions/1) por causa do dataset MusDB — ok para uso livre/pessoal, documentar no README |
| Basic Pitch | Apache 2.0 | [código e modelo](https://pypi.org/project/basic-pitch) — a opção mais limpa |
| madmom | BSD (código) + **CC BY-NC-SA 4.0 (modelos)** | [não comercial](https://arxiv.org/pdf/1605.07008) — aceito pela premissa do projeto |
| music21 | BSD | |
| PyGuitarPro | LGPL | |
| librosa, ffmpeg, mido | ISC / LGPL/GPL (ffmpeg) / MIT | |
| Essentia (se usada) | AGPL | copyleft forte — evitar se possível |

Licença sugerida para o próprio projeto: **MIT ou GPL-3.0**, com aviso claro no
README de que os *modelos* madmom/Demucs têm restrições próprias (quem quiser uso
comercial troca os modelos, não o código).

---

## 5. Roadmap em fases

### Fase 0 — Fundação (1–2 fins de semana)
- Repositório, `pyproject.toml`, estrutura `core/` + `cli/` da seção 2.
- Dataclasses dos contratos (`NoteEvents`, `AnalysisResult`, `TabScore`...) com
  serialização JSON + cache em disco dos resultados intermediários.
- Ambiente: Python 3.10/3.11, PyTorch com CUDA, ffmpeg. Smoke test de GPU.

### Fase 1 — Separar + MIDI (MVP útil desde já)
- `tabgen separar`: Demucs (htdemucs_ft + htdemucs_6s), stems em wav.
- `tabgen transcrever`: Basic Pitch por stem → `NoteEvents` → export MIDI por instrumento.
- Já é útil: dá para abrir o MIDI no TuxGuitar e ouvir o que foi detectado.

### Fase 2 — Análise musical
- madmom: tom, acordes com timestamps, beats/downbeats/BPM.
- `tabgen analisar` imprime relatório (tom, BPM, sequência de acordes) e grava JSON.
- Validar instalação do madmom cedo (risco conhecido de build).

### Fase 3 — Tablatura (entregável principal)
- Quantização das notas na grade de compassos.
- Atribuição corda/casa por programação dinâmica (afinação configurável).
- Export .gp5 via PyGuitarPro (faixas: guitarra, baixo; acordes anotados; armadura; BPM).
- Export MusicXML + tab ASCII.

### Fase 4 — Refinamento
- Técnicas: bends/slides a partir dos pitch bends do Basic Pitch; hammer-on/pull-off
  por heurística de onsets fracos; palm mute fica de fora (precisa de classificador).
- Afinações alternativas, capo, baixo de 5 cordas, violão nylon vs aço.
- Avaliar substituir estágio 4 por modelo específico de guitarra (Riley 2024 / TART).
- Avaliação quantitativa nos datasets da seção 6.

### Fase 5 — Outras interfaces (futuro)
- `web/`: FastAPI + fila de jobs (RQ/Celery); cada estágio vira job; o cache em
  JSON do core já foi desenhado para isso.
- `desktop/`: Tauri (frontend web + core Python via sidecar) ou PySide.

---

## 6. Avaliação: datasets e projetos para estudar

Datasets (medir precisão de verdade, não no ouvido):
- **[GuitarSet](https://arxiv.org/pdf/2204.08094)** — ~3h de violão com anotação
  por corda (captador hexafônico). Benchmark padrão.
- **EGDB** — guitarra elétrica direct-input.
- **[GOAT](https://arxiv.org/html/2509.22655v1)** (2025) — pares áudio + tablatura em escala.
- **[Guitar-TECHS](https://arxiv.org/pdf/2501.03720)** (2025) — técnicas de guitarra elétrica.

Projetos semelhantes para ler o código:
- **[TART](https://arxiv.org/pdf/2510.02597)** — pipeline mais parecido com este plano; acompanhar liberação de código (ISMIR 2026).
- **[Fingerstyle Tab MCP Server](https://glama.ai/mcp/servers/ahzgz77uqu)** (MIT) — usa exatamente Demucs + Basic Pitch; prova o conceito.
- **[tuttut](https://pypi.org/project/tuttut/)** / **[tayuya](https://pypi.org/project/tayuya)** — MIDI→tab heurístico.
- **AutoTab** (UFRN, Brasil) — CNN + otimização em grafo para tab.
- **[amt-tools / guitar-transcription-with-inhibition](https://github.com/cwitkowitz/guitar-transcription-with-inhibition)** — TabCNN de referência.
- **MuseScore 4** — [CLI converte MIDI→MusicXML](https://musescore.org/en/node/296540) (`mscore in.mid -o out.musicxml`); útil como comparação/fallback de quantização.

---

## 7. Limitações realistas (e o que prometer no README)

- **Transcrição não é perfeita**: ~66% F-measure em gravações reais com Basic
  Pitch; fim-a-fim até tab, o estado da arte acadêmico reporta ~54%. A ferramenta
  entrega um **rascunho editável**, não partitura final.
- Funciona melhor com: mix limpo, guitarra em destaque, pouca distorção, andamento estável.
- Sofre com: distorção pesada, muitos instrumentos no mesmo registro, rubato,
  afinações exóticas não informadas.
- Violão vs guitarra no mesmo mix: a separação não distingue bem — v1 trata "stem
  de guitarra" como uma faixa só; o usuário escolhe o instrumento-alvo por flag.
- Sempre revisar no TuxGuitar/Guitar Pro antes de usar. Isso é verdade também para
  as ferramentas comerciais (Songscription etc.) — nenhuma resolve 100%.

## 8. Requisitos de ambiente

- Linux (Ubuntu 24.04 ok), Python 3.10–3.11 (madmom é o limitador), ffmpeg.
- GPU NVIDIA com ≥6 GB VRAM para htdemucs_ft confortável (CPU funciona, ~10–20×
  mais lento). PyTorch com CUDA.
- ~4 GB de disco para pesos de modelos (Demucs ~3 GB, Basic Pitch ~20 MB, madmom ~100 MB).
- Música de 4 min, com GPU: separação ~1–2 min, transcrição segundos, análise
  segundos — pipeline completo em poucos minutos.
