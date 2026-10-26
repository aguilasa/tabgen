---
id: FMVP-TASK-06
---

# FMVP-TASK-06 — Implementar transcrição áudio-notas com Basic Pitch

## Goal

Existe o estágio 4 do pipeline (plano, Estágio 4): `tabgen/core/transcription/` roda o
Basic Pitch sobre um stem wav e produz `NoteEvents` (onset, offset, pitch MIDI, confiança,
pitch bends) serializável e cacheado. Para o stem de baixo, aplica verificação de oitava
(limitar faixa à tessitura do baixo).

## Escopo

- In: wrapper do pacote `basic-pitch` (função `predict`), conversão da saída para `NoteEvents`,
  parâmetros por instrumento (faixa de frequência para baixo vs guitarra), preservação dos
  pitch bends no contrato (base para bends/slides na Fase 4), cache, testes com fixture de
  áudio sintético (senoides geradas em teste — pitch conhecido).
- Out: MIDI em disco (TASK-07); quantização; corda/casa.

## Done criteria

- [ ] Teste com wav sintético (ex.: A4 440 Hz, 1 s) retorna `NoteEvents` contendo nota pitch 69
      com onset <0,2 s de erro.
- [ ] Teste do perfil de baixo: nota sintética E1 (41 Hz) detectada sem salto de oitava
      (pitch 28, não 40).
- [ ] Resultado cacheado: segunda chamada não re-roda o modelo (contador/mock).
- [ ] `pytest -q` e `ruff check .` verdes.

## Notes

Basic Pitch é Apache 2.0 e leve (CPU ok). Dependência `basic-pitch` fixada em versão testada.
Atenção ao conflito potencial de versões de tensorflow/onnx com torch — preferir o backend
ONNX/CoreML se disponível para evitar TF completo.

Verificação (venv `.venv/`, inferência real em CPU sobre senoides geradas no teste):

- `pytest -q tests/test_transcription.py` → `6 passed`: A4 440 Hz → pitch 69 com erro de onset
  <0,2 s; E1 41,2 Hz com perfil de baixo → pitch 28 (sem 40 — sem salto de oitava); cache: 1
  execução do modelo em 2 chamadas (contador); bends round-trip pelo cache JSON.
- `pytest -q` → `39 passed` · `ruff check .` → limpo · grep core puro → vazio, exit 1.

Backend (decisão relevante): basic-pitch 0.4.0 no Linux/py3.11 exige `tensorflow<2.15.1` como
dependência base — dry-run mostrou que instalaria TF 2.15.0.post1 e REBAIXARIA numpy 2.4.6 →
1.26.4 (conflito com torch 2.14.1). Resolução: `pip install --no-deps basic-pitch==0.4.0` +
deps reais do caminho ONNX (onnxruntime 1.31.0, librosa 0.11.0, pretty-midi, mir-eval,
resampy); sem TF, basic-pitch auto-seleciona o modelo `nmp.onnx` embarcado. numpy intacto.
Pin documentado em comentário no `pyproject.toml` (fora da lista resolvível de propósito —
listá-lo puxaria TF).

Desenho: `transcribe(input, instrument, …) -> (TranscriptionResult, cache_hit)`; cache estágio
"transcription", versão `basic-pitch-icassp2022-onnx-{instrument}` (guitar/bass não colidem).
Perfis: guitar 60–2000 Hz; bass 28–400 Hz (com faixa de guitarra o E1 simplesmente some — o
perfil é o que faz grave cair certo). Bends (bins de 1/3 de semitom) preservados em
`TranscriptionResult.bends` paralelo às notas — `Note` não tem campo bends e `models.py` estava
fora do escopo. `predict()` do basic_pitch imprime banner; embrulhado em redirect_stdout.

Encaminhamentos: campo `bends` em `models.py` (contrato normal para a Fase 4); README precisa
do passo `pip install --no-deps basic-pitch==0.4.0` (TASK-08); doctor poderia checar
basic-pitch+onnxruntime importáveis e ausência de tensorflow (opcional).

## Execution Log

- **Closed** — commit `698b17d` (2026-10-26): feat(transcription): add Basic Pitch audio-to-notes stage with ONNX backend
  - Files (`git show --name-status 698b17d`):
    - `M pyproject.toml`
    - `M tabgen/core/transcription/__init__.py`
    - `A tabgen/core/transcription/basic_pitch.py`
    - `A tests/test_transcription.py`
