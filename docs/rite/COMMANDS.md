# Comandos dos ciclos

Os comandos de cada ciclo do Rite, do nascimento ao arquivo, na ordem do roadmap do
[`/docs/planejamento/audio-para-tablatura.md`](/docs/planejamento/audio-para-tablatura.md) §5.
Um ciclo só se cria **quando a fase abre**: antes disso, a seção da fase no plano é só um esboço
de tópicos e o `plan-to-tasks` não tem de onde tirar critérios de pronto verificáveis.

Os comandos `/rite:...` são skills do Claude Code. Os de shell rodam no zsh, a partir da raiz do
repositório:

```sh
rite(){ sh "$(ls -d "$HOME"/.claude/plugins/cache/rite/rite/*/ | sort -V | tail -1)bin/rite" "$@"; }
```

A função usa a versão mais nova do plugin instalada em `~/.claude/plugins/cache/rite/rite/`, sem
número fixo no texto; `ls` nessa pasta mostra qual é.

Configuração relevante do `rite.toml`: commits sem trailer `Co-Authored-By`
(`co_author_footer = false`) e **push automático depois de cada item** (`push = "after-each-item"`):
`rite finish` e `rite commit-new` enviam para o `origin` (github.com/aguilasa/tabgen).

## Fases

| Fase | Ciclo | Prefixo | Seção do plano | Estado |
| ---: | --- | --- | --- | --- |
| 0–1 | `fundacao-mvp` | `FMVP` | §5 Fase 0 + Fase 1 | aberto: 8 tasks planejadas (FMVP-TASK-01 a 08) |
| 2 | `analise-musical` | `ANA` | §5 Fase 2; §3 Estágios 2–3 | esboço; detalhar ao fechar `fundacao-mvp` |
| 3 | `tablatura` | `TAB` | §5 Fase 3; §3 Estágios 5–6 | esboço |
| 4 | `refinamento` | `REF` | §5 Fase 4; §6 (avaliação) | esboço |
| 5 | `interfaces` | `UI` | §5 Fase 5; §2 (camadas) | futuro, opcional |

As fases são sequenciais: a 2 usa os contratos e o cache da 0, a 3 precisa da grade de compassos
da 2 e das notas da 1, a 4 refina a 3. A Fase 5 (web/desktop) só abre depois de o pipeline de
CLI estar completo. Os prefixos de 2 a 5 são sugestões; confirme cada um ao criar o ciclo. O
prefixo entra em todo ID do ciclo (`<PREFIXO>-TASK-NN`, `FIX-<PREFIXO>-NNN`) e não muda depois sem
renomear os arquivos.

## O ciclo de vida, igual em toda fase

Troque `<ciclo>` e `<PREFIXO>` pela linha da fase na tabela acima.

**0. Antes de abrir.** A seção da fase no plano (§5) precisa de entregas concretas, com critério
de pronto verificável para cada uma. Escrevê-las é trabalho de plano, fora do Rite; a task de
fechamento da fase anterior é o momento natural de refinar a seguinte.

**1. Criar o ciclo.** Pela skill, que também semeia o profile e faz os commits:

```
/rite:new-cycle <ciclo> --prefix <PREFIXO> --plan docs/planejamento/audio-para-tablatura.md
```

Ou pela CLI, que só cria pasta, views, profile e pitfalls:

```sh
rite new-cycle <ciclo> --prefix <PREFIXO> --plan docs/planejamento/audio-para-tablatura.md --commit --json
```

Ao semear o profile, leve do ciclo anterior os pitfalls que a retro mandou guardar
(`--pitfalls-from <ciclo-anterior>`; os de `fundacao-mvp` ficam em
`docs/rite/profiles/fundacao-mvp.pitfalls.md`).

**2. Quebrar o plano em tasks.**

```
/rite:plan-to-tasks docs/planejamento/audio-para-tablatura.md <ciclo> --dry-run
/rite:plan-to-tasks docs/planejamento/audio-para-tablatura.md <ciclo>
```

O campo `phase` das tasks é só o número (`2`, não `Fase 2`); os checks do profile usam o rótulo
`### Fase 2 — ...` (`[sections].phase_label = "Fase"`). Uma task `closing` por fase, dependendo
de todas as outras da fase.

**3. Executar.** Uma task por vez, ou um lote pequeno em ondas sem conflito:

```
/rite:execute <ciclo>
/rite:execute <ciclo> <PREFIXO>-TASK-NN
/rite:execute-batch <ciclo> 2
/rite:execute-batch <ciclo> --plan
```

`tabgen/cli/main.py`, `pyproject.toml` e `tabgen/core/pipeline.py` são hot files (profile): tasks
que os tocam serializam no lote. Tasks que rodam modelos na GPU (Demucs) não devem rodar em
paralelo — se virar regra, declarar recurso `gpu` em `[resources]` do `rite.toml`.

**4. Revisar.** Cada task feita ganha revisão independente, que abre as fixes:

```
/rite:review <ciclo>
/rite:review <ciclo> <PREFIXO>-TASK-NN
/rite:review-all <ciclo>
```

**5. Corrigir.** Todas as fixes abertas (triagem, reprodução, ondas), ou uma só:

```
/rite:fix-all <ciclo>
/rite:fix-all <ciclo> --plan
/rite:fix <ciclo> FIX-<PREFIXO>-NNN
```

Repita 3 a 5 até não sobrar task nem fix. Para saber o próximo comando a qualquer momento:

```
/rite:status <ciclo>
/rite:phase <ciclo> <fase>
/rite:board
```

```sh
rite status --all --json
rite gates --json
rite check --cycle <ciclo> --json
```

Gates do ciclo (profile): `pytest -q` e `ruff check .`.

**6. Retro.** Agrupa as fixes por causa raiz e propõe o que guardar, promover, reportar e podar:

```
/rite:retro <ciclo>
```

**7. Fechar.** Confere as precondições, move a pasta para `docs/rite/cycles/archive/` e reescreve
os links:

```
/rite:close-cycle <ciclo>
```

```sh
rite archive <ciclo> --dry-run --json
rite check --all --json
```

O `archive` só reescreve links; caminhos citados em comentários de código continuam no endereço
antigo e se corrigem à mão.

## Fases 0–1 — `fundacao-mvp` (aberto)

Criado assim:

```sh
rite new-cycle fundacao-mvp --prefix FMVP --plan docs/planejamento/audio-para-tablatura.md --commit --json
```

```
/rite:plan-to-tasks docs/planejamento/audio-para-tablatura.md fundacao-mvp
```

Oito tasks: Fase 0 = estrutura do pacote (01), contratos + cache (02), `tabgen doctor` (03) e
fechamento (04, `closing`); Fase 1 = separação Demucs (05), transcrição Basic Pitch (06), export
MIDI + `tabgen transcribe` (07) e fechamento (08, `closing`). Próximos passos:

```
/rite:execute fundacao-mvp
/rite:review fundacao-mvp
/rite:fix-all fundacao-mvp
/rite:retro fundacao-mvp
/rite:close-cycle fundacao-mvp
```

O fechamento da Fase 1 (FMVP-TASK-08) é o momento de detalhar a §5 Fase 2 do plano.

## Fase 2 — `analise-musical`

Tom, acordes, beats/downbeats e BPM com madmom; `tabgen analyze`.

```
/rite:new-cycle analise-musical --prefix ANA --plan docs/planejamento/audio-para-tablatura.md --pitfalls-from fundacao-mvp
```

```
/rite:plan-to-tasks docs/planejamento/audio-para-tablatura.md analise-musical
```

Validar a instalação do madmom na primeira task (risco de build com Python novo, plano §3).

## Fase 3 — `tablatura`

Quantização na grade de compassos, atribuição corda/casa por programação dinâmica, export
`.gp5` (PyGuitarPro), MusicXML e tab ASCII.

```
/rite:new-cycle tablatura --prefix TAB --plan docs/planejamento/audio-para-tablatura.md --pitfalls-from analise-musical
```

```
/rite:plan-to-tasks docs/planejamento/audio-para-tablatura.md tablatura
```

## Fase 4 — `refinamento`

Técnicas (bend/slide/hammer-on), afinações alternativas, avaliação em GuitarSet/EGDB, troca do
modelo de transcrição se houver ganho medido.

```
/rite:new-cycle refinamento --prefix REF --plan docs/planejamento/audio-para-tablatura.md --pitfalls-from tablatura
```

```
/rite:plan-to-tasks docs/planejamento/audio-para-tablatura.md refinamento
```

## Fase 5 — `interfaces` (futuro)

Camada `web/` (FastAPI + fila de jobs) e/ou `desktop/` sobre o mesmo `core`.

```
/rite:new-cycle interfaces --prefix UI --plan docs/planejamento/audio-para-tablatura.md --pitfalls-from refinamento
```

```
/rite:plan-to-tasks docs/planejamento/audio-para-tablatura.md interfaces
```

Depois de criado, cada ciclo segue os passos 3 a 7 do ciclo de vida acima.
