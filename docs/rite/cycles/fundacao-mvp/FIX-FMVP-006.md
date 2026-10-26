---
id: FIX-FMVP-006
---

# FIX-FMVP-006 — Atualizar README com tempos reais medidos no e2e da Fase 1

Origin: [FMVP-TASK-08](/docs/rite/cycles/fundacao-mvp/08-fechar-fase-1.md)

## Problem

O README (linhas 138–150) ainda diz "real-music timings will be added once Phase 1 is validated
end to end" e mantém "4-minute song, separation (estimate) ~1–2 min", mas a própria
FMVP-TASK-08 validou a Fase 1 de ponta a ponta e mediu 47 s de separação / 61,3 s total para uma
música de 4 min 08 s (registrado nas Notes da task). O commit de trabalho `1d4bdd3` (12:06)
precede a rodada com música real (artefatos de 16:13) e o README nunca foi revisitado, embora o
Escopo inclua "atualização do README (uso, exemplos, tempos esperados)". A estimativa publicada
é ~2× o valor medido e a promessa ficou permanentemente não cumprida.

## Evidência

```text
$ sed -n '136,150p' README.md
synthetic 10-second sample; real-music timings will be added once Phase 1 is
validated end to end:
| 4-minute song, separation (estimate)  | ~1–2 min        |
```

## Root cause

Hipótese (não provada): o commit do README foi feito enquanto a task estava blocked esperando o
e2e; depois do e2e e da confirmação no TuxGuitar a task foi fechada sem um commit de follow-up
dobrando os números medidos de volta no README.

## Fix

Editar a seção "Expected runtimes" de `README.md`: substituir a cláusula "will be added" e a
linha "(estimate) ~1–2 min" pelos números medidos no e2e (música de 4 min 08 s, RTX 3060
Laptop: ~61 s total frio, ~47 s separação, ~1,5 s quente).

## Arquivos

- `README.md`

## Verificação

```text
$ ! grep -q "real-music timings will be added" README.md
```

Falha hoje; deve passar depois do fix.

Medido após o fix (2026-10-26):

```text
$ ! grep -q "real-music timings will be added" README.md; echo "exit=$?"
exit=0
```

## Notas

Seção "Expected runtimes" atualizada: intro menciona a música real de 4 min 08 s do e2e da
Fase 1; linha de estimativa substituída por medidos — frio ~61 s total (≈47 s separação,
≈6 s guitar + ≈4 s bass) e quente ~1,5 s. Linhas da amostra sintética e notas (download ~1 GB,
CPU 10–20×) mantidas.

Encaminhamento do sweep (fora do escopo): `docs/planejamento/audio-para-tablatura.md:343` ainda
diz "separação ~1–2 min" (estimativa do plano vs ~47 s medido) — documento de planejamento,
não corrigido aqui.

## Execution Log

- 2026-10-26 — Triagem (`rite reproduce FIX-FMVP-006`): REPRODUCED.

  ```text
  $ sed -n '136,150p' README.md
  ...synthetic 10-second sample; real-music timings will be added once Phase 1 is
  validated end to end:
  | 4-minute song, separation (estimate)  | ~1–2 min        |
  ```
- **Closed** — commit `8b39081` (2026-10-26): docs(readme): replace runtime estimates with measured Phase 1 e2e timings
  - Files (`git show --name-status 8b39081`):
    - `M README.md`
