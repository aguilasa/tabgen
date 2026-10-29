---
id: UI-TASK-05
---

# UI-TASK-05 — Implementar abas de resultados com prévia ASCII e exports

## Goal

As abas de resultados existem conforme o protótipo: Stems (5 stems com caminho e "abrir
pasta"), Análise (tom + confiança com aviso de `switched`, BPM, beats/downbeats, tabela de
acordes com filtro de `N`), Notas (contagem, transcriber, caminho do .mid por instrumento) e
Tablatura (resumo por faixa: notas, afinação, capo, não atribuídas, técnicas; prévia ASCII
rolável do `ascii_preview`; botões de export gp5/MusicXML/ASCII que chamam o worker).

## Escopo

- In: render dos payloads do worker (summaries serializados); "abrir pasta" via API do Tauri;
  exports re-invocando o worker com o formato pedido (cache quente esperado); estados vazios
  (estágio ainda não rodado).
- Out: player por stem, tab renderizada (v2); opções de geração (06).

## Done criteria

- [x] Após uma execução real da amostra, cada aba mostra os dados do summary (screenshots nas
      Notes); o aviso de tom trocado aparece quando `key_check.switched` é true (dado simulado em
      teste de componente ou música que troque).
- [x] Exportar MusicXML a partir do resultado gp5 reusa o cache (<5 s) e grava o arquivo
      (verificado reabrindo com music21 via worker ou CLI).
- [x] "Abrir pasta" abre o diretório do artefato no gerenciador de arquivos.
- [x] `npm run build` e typecheck do frontend saem 0.

## Notes

Prévia ASCII usa a string pronta do worker — a UI nunca formata tablatura (regra: lógica
musical só no core).

Da UI-TASK-04: `RunState.result` (em `desktop/src/lib/run.ts`, hook `useTablatureRun` no App) já traz o `TablatureResult` completo do worker (scores, beat_grids, key_check, unassigned, ascii_preview, output_path, format, cache_hit) para a música do caminho atual; `components/Pipeline.tsx` mostra hoje uma linha de resultado que as abas podem substituir.

Implementado por rite-worker (onda 1 do batch com UI-TASK-06; ondas separadas porque ambas mexem
em `Musica.tsx`, `run.ts`, `App.tsx` e no worker).

Decisões:

- Core intocado; três acréscimos ao worker (docstring do protocolo atualizada, 4 testes novos):
  `analyze` ganha `stems` (nome → wav, lidos da entrada de cache da separação; `{}` se ela não
  vale mais — usa o privado `separation.demucs._cached_result_is_valid`); `transcribe` ganha
  `transcriber` por instrumento; `tablature` ganha `tracks` (notas, nome/notas da afinação via
  `TUNING_PRESETS` e `ascii_tab._pitch_name`, capo, não atribuídas, técnicas por tipo).
- Após um tablature, a UI (`useRunDetails` em `run.ts`) chama `analyze` e `transcribe` (cache
  quente; o `transcribe` grava os `.mid` na pasta da saída). Exports (`useExports`) reenviam o
  tablature com os mesmos args + `output`/`format`. A UI não formata tablatura nem nomes de nota.
- "Abrir pasta": comando Rust `open_folder` → `xdg-open <dir>`.
- "Compassos" mostra a contagem de downbeats da análise (o maior número de compasso da partitura
  subconta: notas antes do primeiro downbeat caem no compasso 0).

Verificação (Xvfb `:99`, binário debug, `XDG_DATA_HOME` isolado, amostra senoidal de 10 s):

- Cada aba após "Concluído 14,3 s": `evidencias/05-stems.png` (5 stems + abrir pasta),
  `05-analise.png` (A major, confiança 68%, 62,5 BPM, 10 beats, 2 compassos, filtro N),
  `05-notas.png` (contagem, transcriber, caminhos `.mid`), `05-tablatura.png` (resumo por faixa,
  prévia ASCII, exports). A própria amostra tem `key_check.switched` true: aviso "Tom trocado na
  checagem. O madmom indicou D minor, mas o histograma … aponta A major" aparece com dado real.
- MusicXML do cache, reproduzido pelo main thread em diretório novo:
  `printf '{"cmd":"tablature","args":{"input":"$D/sample.mp3","output":"$D/sample.gp5"}}\n' | .venv/bin/python -m tabgen.worker`
  → `cache_hit False`; mesma requisição com `"output":"$D/sample.musicxml"` → `musicxml
  cache_hit True` em `.374 s` (`date +%s.%N`); `music21 converter.parse(...).parts` → `2`. Na UI:
  "musicxml gravado em …/sample.musicxml (tablatura do cache, 0,4 s)". Probe versionado: fix aberto.
- Abrir pasta: app com `xdg-open` falso no `PATH` que só registra o argumento → clique em
  "abrir pasta" do stem guitarra registrou `xdg-open …/song/stems`; no export, `xdg-open …/song`.
- `npm run typecheck` rc 0; `npm run build` → `✓ built`; `cargo clippy -q` sem saída;
  `cargo fmt --check` rc 0; `.venv/bin/pytest -q` → `241 passed`; `ruff check .` limpo; grep de
  pureza do core vazio.

## Execution Log

- **Closed** — commit `542fc20` (2026-10-29): feat(desktop): add result tabs with stems, analysis, notes, ASCII preview and exports
  - Files (`git show --name-status 542fc20`):
    - `M desktop/src-tauri/src/lib.rs`
    - `M desktop/src/App.css`
    - `M desktop/src/App.tsx`
    - `A desktop/src/components/Analise.tsx`
    - `A desktop/src/components/Notas.tsx`
    - `A desktop/src/components/Stems.tsx`
    - `A desktop/src/components/Tablatura.tsx`
    - `M desktop/src/lib/run.ts`
    - `M desktop/src/lib/worker.ts`
    - `M desktop/src/screens/Musica.tsx`
    - `M docs/rite/cycles/interface-desktop/05-implementar-abas-de-resultados-com-previa-ascii.md`
    - `M docs/rite/cycles/interface-desktop/06-implementar-painel-de-opcoes-de-geracao.md`
    - `A docs/rite/cycles/interface-desktop/evidencias/05-analise.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/05-notas.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/05-stems.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/05-tablatura.png`
    - `M tabgen/worker/__init__.py`
    - `M tests/test_worker.py`
  - **Files amended** — added to `files`:
    - `docs/rite/cycles/interface-desktop/06-implementar-painel-de-opcoes-de-geracao.md`
- **Reviewed** (2026-10-29) at `7935ca6`: no finding
