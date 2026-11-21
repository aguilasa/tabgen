---
id: UI-TASK-06
---

# UI-TASK-06 — Implementar painel de opções de geração

## Goal

O painel "Gerar tab ▶" existe conforme o protótipo: instrumentos (guitarra/baixo), afinação da
guitarra (presets reais + custom com validação), afinação do baixo (incl. five-string), capo
0–12, tipo de guitarra (elétrica/nylon/aço), transcriber (riley/basic-pitch), técnicas on/off,
device (auto/cuda/cpu), caminho de saída com formato pelo sufixo ou seletor. As escolhas vão na
requisição NDJSON e ficam lembradas por música.

## Escopo

- In: presets de `TUNING_PRESETS` expostos pelo worker (cmd auxiliar ou constante no payload do
  doctor — decidir na execução); validação do custom espelhando `resolve_tuning` (erro do worker
  exibido no campo); persistência das últimas opções; estimativa de tempo exibida (fria vs cache).
- Out: perfis de preset salvos pelo usuário (v2).

## Done criteria

- [x] Gerar com drop-d + capo 2 + nylon produz .gp5 cuja afinação/capo/programa GM conferem
      (reaberto via guitarpro no teste do worker ou CLI).
- [x] Afinação custom inválida (ex.: ordem decrescente) mostra o erro do worker no campo, sem
      rodar o pipeline.
- [x] Trocar transcriber invalida o cache (execução seguinte fria nos estágios de transcrição).
- [x] Reabrir a música mostra as últimas opções usadas.
- [x] `npm run build` e typecheck do frontend saem 0.

## Notes

Fonte única dos presets é o core (worker expõe) — nada de duplicar listas de afinação no JS.
Pitfall herdado: comparar valores parseados, não strings.

Da UI-TASK-04: o botão "Gerar tab ▶" chama `useTablatureRun.start(path)`, que monta os args com `tablatureArgs(path, prefs)` em `desktop/src/lib/run.ts`; o drawer deve estender essa função ou dar um argumento de opções ao `start`.

Da UI-TASK-05: `tablatureArgs(path, prefs)` em `desktop/src/lib/run.ts` monta os args e os
guarda em `RunState.args`; exports (`useExports`) e os jobs de detalhe (`detailArgs`) os
reaproveitam — estender `tablatureArgs` com instrumentos/afinações/capo/técnicas/guitar_type/saída
propaga para eles. Formato→sufixo: `exportPath`/`EXPORT_SUFFIX` em `run.ts`. Comando de presets:
`COMMANDS` e `_HANDLERS` em `tabgen/worker/__init__.py` e `WorkerCmd` em `worker.ts`;
`tracks[].tuning_name` já casa com `TUNING_PRESETS`.

Implementado por rite-worker (onda 2 do batch com UI-TASK-05).

Decisões:

- Worker ganha `presets` (instrumentos, afinações por instrumento com MIDI e notas, tipos de
  guitarra, transcribers, formatos com sufixo, faixa de capo — tudo das constantes do core) e
  `tuning` (`resolve_tuning` direto; nome do preset casado por valor MIDI, não por string).
  `tablature` passa a recusar capo fora de 0–12 e afinação que não seja string ou lista de ints,
  antes de qualquer progress. O JS não guarda listas de afinação, tipos, transcribers ou formatos.
- Opções por música em `localStorage` (`tabgen.songOptions`: caminho → opções, duração e cache da
  última execução; 50 mais recentes), em `run.ts`; `useTablatureRun.start(path, options?)` e
  `tablatureArgs(path, prefs, options?)`. Exports e jobs de detalhe herdam via `RunState.args`.
- Estimativa fria: linha "Expected runtimes" do README (export de 4:08 frio = 193 s, RTX 3060
  Laptop) escalada pela duração; quente "< 1 s" do README; mais a última execução medida. Na amostra
  de 10 s subestima (~8 s vs 13,6 s) pelo custo fixo de carregar modelos.
- Capability nova: `dialog:allow-save` (seletor de saída). A faixa de capo agora existe na CLI
  (`--capo min=0 max=12`) e no worker (`CAPO_RANGE`): duas cópias do mesmo limite.

Verificação (worker reproduzido pelo main thread em diretórios novos; UI em Xvfb `:99`):

- `printf '{"cmd":"tablature","args":{"input":"$D/sample.mp3","output":"$D/sample.gp5","tunings":{"guitar":"drop-d"},"capos":{"guitar":2},"guitar_type":"nylon"}}\n' | .venv/bin/python -m tabgen.worker`
  e `guitarpro.parse` → `[64, 59, 55, 50, 45, 38] 2 24` (cordas drop-d, capo em `offset`, GM 24
  nylon). Teste `test_tablature_writes_tuning_capo_and_guitar_program_to_gp5`. Gerado pelo app:
  `evidencias/06-drawer-dropd-capo2-nylon.png`, `06-gerado-dropd-capo2-nylon.png`.
- `echo '{"cmd":"tuning","args":{"instrument":"guitar","spec":"E4,B3"}}' | .venv/bin/python -m tabgen.worker`
  → `{"type": "error", "kind": "PipelineError", "message": "tuning must be ordered low-to-high
  (thickest string first): 'E4,B3'"}`; na UI o erro aparece no campo e "Gerar ▶" fica desabilitado,
  sem `.tabgen/` criado (`evidencias/06-custom-invalida.png`); teste confirma tablature com afinação
  decrescente → uma linha de erro, nenhum progress, separate_fn não chamado.
- Troca de transcriber, basic-pitch → riley em diretório novo (primeiro pct de cada estágio):
  riley `cache_hit False`, `separation` e `transcription:bass` do cache, `transcription:guitar`
  rodou (`evidencias/06-troca-transcriber-riley.png`). No sentido riley → basic-pitch a
  transcrição Basic Pitch da guitarra sai do cache (o riley já roda Basic Pitch para os bends) e a
  tablatura recalcula (`cache_hit False`) — reuso legítimo.
- Reabrir o app com o mesmo `XDG_DATA_HOME`: cabeçalho "Últimas opções: guitarra drop-d, capo 2,
  nylon · baixo standard · riley · técnicas · auto · gp5" e o painel reabre com elas
  (`evidencias/06-reaberta-ultimas-opcoes.png`). Extra: custom "38, 45, D3, G3, B3, E4" = drop-d,
  cache da tablatura em 0,2 s (`evidencias/06-custom-igual-dropd-cache.png`).
- `npm run typecheck` rc 0; `npm run build` → `✓ built`; `cargo clippy -q` sem saída;
  `cargo fmt --check` rc 0; `.venv/bin/pytest -q` → `260 passed`; `ruff check .` limpo; grep de
  pureza do core vazio. Números e2e cobertos por `scripts/probe_e2e_worker.py` via FIX-UI-008
  (gp5 drop-d+capo2+nylon reaberto, troca de transcriber, cache da tablatura <5 s); o export
  MusicXML do cache (critério 2 da UI-TASK-05) segue em FIX-UI-007.

## Execution Log

- **Closed** — commit `dfb5906` (2026-10-29): feat(desktop): add generation options drawer with worker presets and tuning validation
  - Files (`git show --name-status dfb5906`):
    - `M desktop/src-tauri/capabilities/default.json`
    - `M desktop/src/App.css`
    - `M desktop/src/App.tsx`
    - `A desktop/src/components/OpcoesDrawer.tsx`
    - `M desktop/src/lib/run.ts`
    - `M desktop/src/lib/worker.ts`
    - `M desktop/src/screens/Musica.tsx`
    - `M docs/rite/cycles/interface-desktop/06-implementar-painel-de-opcoes-de-geracao.md`
    - `A docs/rite/cycles/interface-desktop/evidencias/06-custom-igual-dropd-cache.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/06-custom-invalida.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/06-drawer-dropd-capo2-nylon.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/06-gerado-dropd-capo2-nylon.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/06-reaberta-ultimas-opcoes.png`
    - `A docs/rite/cycles/interface-desktop/evidencias/06-troca-transcriber-riley.png`
    - `M tabgen/worker/__init__.py`
    - `M tests/test_worker.py`
- **Reviewed** (2026-10-29) at `2d2bf49`: FIX-UI-008, FIX-UI-009
