---
id: ANA-TASK-06
---

# ANA-TASK-06 — Fechar Fase 2

## Goal

A Fase 2 está verificada com música real: `tabgen analyze` roda de ponta a ponta na GPU sobre
uma gravação escolhida pelo usuário, tempos medidos, checks e gates da fase verdes, e README
atualizado com uso e tempos medidos do `analyze`.

## Escopo

- In: rodada e2e com música real; tempos por estágio com o comando que os mede; conferência
  manual do tom/BPM/acordes pelo usuário; checks da Fase 2 do profile; README (uso, exemplo de
  saída, tempos medidos); `doctor` e instalação em venv limpa.
- Out: melhorias de qualidade (Fase 4); novos recursos.

## Done criteria

- [x] `.venv/bin/tabgen analyze <música real>.mp3` sai 0 na GPU; tempos (frio e quente) anotados
      com o comando de medição.
- [x] Usuário confirma tom e BPM da música real (verificação manual registrada nas Notes).
- [x] Todos os checks da Fase 2 do profile passam.
- [x] Venv limpa: instalação documentada (incl. madmom) sai 0 e `.venv/bin/pytest -q` verde.
- [x] `! grep -qi "will be added" README.md` e README tem seção do `analyze` com tempos medidos.
- [x] `.venv/bin/pytest -q` e `.venv/bin/ruff check .` verdes.

## Notes

Pitfall herdado (FIX-FMVP-006): números medidos no e2e vão para o README neste mesmo item, não
depois.

### Verificação (2026-10-26)

- **E2e música real** — "You and I.flac" (4 min 08 s), GPU RTX 3060 Laptop. Frio (caches
  apagados): `/usr/bin/time -f "elapsed=%es" .venv/bin/tabgen analyze "You and I.flac"` →
  `elapsed=140.01s`, exit 0 (separação ≈45 s, beats ≈27 s, harmonia ≈64 s — barras do rich).
  Quente: mesmo comando → `cache hit: analysis reused, madmom skipped.`, `elapsed=0.26s`.
  Resultado: `Key: F# major (confidence 0.86)`, `Tempo: 139.5 BPM (580 beats, 145 downbeats)`,
  97 segmentos de acordes (início: F#:maj → B:maj → D#:min → C#:maj).
- **Verificação manual do usuário** — Moises.ai reporta Gb maior, 139 BPM, sequência
  Gb–Cb–Ebm–Db; enarmonicamente idêntico a F# maior e F#:maj–B:maj–D#:min–C#:maj. Confirmado.
- **Checks Fase 2 do profile** — `from madmom.features import downbeats, key, chords` ok;
  `analyze sample.mp3` exit 0 e `AnalysisResult.from_json` recarrega ("reloaded: D minor 62.5 1
  chord segments"); 2ª execução `cache hit`, 0.19 s (<5 s); click 120 BPM:
  `pytest -q tests/test_analysis_beats.py` → 6 passed; grep de pureza do core vazio (exit 1).
- **Venv limpa** — python3.11 -m venv + `pip install -e ".[dev]"` + `pip install --no-deps
  basic-pitch==0.4.0` em diretório de scratch: instalação exit 0, `pytest -q` → 77 passed.
- **Doctor** — `.venv/bin/tabgen doctor` exit 0.
- **Gates** — `.venv/bin/pytest -q` → 77 passed; `.venv/bin/ruff check .` → "All checks
  passed!"; `! grep -qi "will be added" README.md` passa; README ganhou seção
  "Analyze a song (key, tempo, chords)" e duas linhas de runtimes medidos.

## Execution Log

- **Closed** — commit `80b72ba` (2026-10-26): docs(readme): document analyze command with measured runtimes
  - Files (`git show --name-status 80b72ba`):
    - `M README.md`
    - `M docs/rite/cycles/analise-musical/06-fechar-fase-2.md`
