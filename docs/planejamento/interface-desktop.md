# Interface desktop (tabgen Studio) — especificação da Fase 5

> Spec aprovada pelo usuário em 2026-10-28, a partir do protótipo navegável
> <https://claude.ai/artifact/7AvMdpWdyaD56TYHeikJou> (dados fictícios; cada controle
> corresponde a uma opção real da CLI/core). Stack decidida: **Tauri**.
> Complementa o plano geral: [audio-para-tablatura.md](/docs/planejamento/audio-para-tablatura.md),
> seções 2 (arquitetura) e 5 (Fase 5).

## 1. Visão e escopo da v1

Aplicativo desktop de janela única ("tabgen Studio") que espelha o pipeline completo da CLI:
abrir uma música (mp3/wav/flac), rodar separação/análise/transcrição/exportação com progresso
por estágio, ver os resultados (stems, tom/BPM/acordes, notas, prévia ASCII da tablatura) e
exportar .gp5/MusicXML/ASCII. Verificação de ambiente (doctor) integrada.

Fora da v1 (ideias de v2, anotadas no protótipo): player de áudio por stem, tablatura
renderizada (pauta TAB desenhada), biblioteca com busca e fila de músicas, edição da tab.
A avaliação (`scripts/eval/`) permanece só na CLI.

## 2. Stack e arquitetura

- **Tauri 2** (frontend web) + **sidecar Python**: a UI nunca contém lógica musical
  (plano geral, seção 2, regra 3); todo trabalho roda num processo worker Python que consome
  `tabgen.core`.
- Árvore: `desktop/` ao lado de `cli/` (plano geral, seção 2); o worker é um módulo Python novo
  `tabgen/worker/` — camada fina como a `cli/`, permitida a fazer I/O (o `core` continua puro).
- A v1 usa a instalação Python existente do tabgen (venv): o app localiza o interpretador
  configurado e o doctor orienta quando faltar algo. Empacotar o Python junto fica para depois.
- Cancelamento: o core não tem API de cancelamento; cancelar = encerrar o processo worker.
  Estágios já concluídos permanecem no cache `.tabgen/`.

## 3. Protocolo UI ↔ worker

- Worker: `python -m tabgen.worker`, um job por processo, falando **NDJSON** (uma mensagem JSON
  por linha) em stdin/stdout:
  - requisição (uma por processo): `{"cmd": "doctor" | "analyze" | "transcribe" | "tablature",
    "args": {…}}` com os mesmos parâmetros das funções `run_*` do core (afinações, capo,
    guitar_type, transcriber, techniques, device, output…).
  - eventos: `{"type": "progress", "stage": "<nome real do estágio>", "pct": 0–100}` — mapeia
    1:1 o callback `on_progress` do core.
  - fim: `{"type": "result", …summary.to_dict()…}` ou `{"type": "error", "kind":
    "<ExceptionName>", "message": "…"}`; exit 0/1.
- Summaries serializados com os contratos existentes (`to_dict`); a prévia ASCII vem de
  `render_ascii_tab()` no payload do resultado de tablatura.

## 4. Telas

Conforme o protótipo aprovado:

1. **Início** — arrastar/escolher arquivo (mp3/wav/flac), lista de recentes (persistida pela
   UI), badge do ambiente (resumo do doctor) no topo.
2. **Música (workspace)** — cabeçalho com o arquivo e o botão "Gerar tab ▶"; abas:
   - *Visão geral*: cartão por estágio (pendente/cache/rodando/ok/erro) e barras de progresso
     por estágio real do core; cancelar.
   - *Stems*: 5 stems com caminho e "abrir pasta".
   - *Análise*: tom + confiança (aviso quando `key_check.switched`), BPM, beats/downbeats,
     compassos, tabela de acordes com filtro dos trechos `N`.
   - *Notas*: por instrumento, contagem, transcriber usado, caminho do .mid.
   - *Tablatura*: resumo por faixa (notas, afinação, capo, não atribuídas, técnicas), prévia
     ASCII rolável, botões de export gp5/MusicXML/ASCII.
3. **Opções de geração** (painel lateral do "Gerar tab ▶") — instrumentos, afinação da
   guitarra (presets + custom), afinação do baixo (incl. five-string), capo 0–12, tipo de
   guitarra (elétrica/nylon/aço), transcriber (riley/basic-pitch), técnicas on/off, device
   (auto/cuda/cpu), caminho e formato de saída (formato segue o sufixo).
4. **Ambiente** — os 5 checks do doctor com detalhe, "verificar de novo", padrões persistidos
   da UI (device, transcriber, pasta de saída).

## 5. Empacotamento e verificação

- Build Linux via `tauri build` (deb/AppImage); CI fica fora da v1.
- A verificação de cada entrega usa o worker como fronteira testável (pytest, sem Tauri) e
  o app via `tauri dev` para a parte visual; o fechamento da fase roda o fluxo completo com
  música real e confirmação manual do usuário.

## 6. Roadmap da Fase 5 (desktop)

1. Worker NDJSON (`tabgen/worker/`) com testes — fronteira entre UI e core.
2. Scaffold do app Tauri em `desktop/` com sidecar funcionando (tela Ambiente/doctor como
   primeira fatia de ponta a ponta).
3. Tela Início (abrir arquivo, recentes).
4. Workspace com progresso e cancelamento.
5. Abas de resultados (stems, análise, notas, tablatura com prévia e exports).
6. Painel de opções completo.
7. Build/empacotamento Linux.
8. Fechamento: e2e com música real no app.
