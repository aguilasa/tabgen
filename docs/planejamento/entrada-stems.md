# Entrada de stems já separados

## Problema

O tabgen sempre roda o Demucs. Quem já separou as faixas em outra ferramenta (Moises.ai: `rhythm`,
`lead`, `bass`; ou stems próprios) hoje passa o stem como áudio de entrada, e o Demucs separa de novo
um arquivo que já é só guitarra. Isso gasta cerca de 45 s por música, e pode piorar o resultado: o
`htdemucs_6s` às vezes manda parte da guitarra para `other`.

Caso real (29/10/2026): `you-and-i-rhythm-…wav` e `you-and-i-lead-…wav`, saídas do Moises, viraram dois
`.gp5` passando cada wav como entrada.

## Decisões

1. **Flag `--stem INSTRUMENTO=ARQUIVO`**, repetível, em `tabgen export`, `tabgen transcribe` e
   `tabgen analyze`. INSTRUMENTO é `guitar` ou `bass` (os de `TABLATURE_INSTRUMENTS`). O arquivo
   precisa existir; caminho relativo ao diretório atual.
2. **Flag `--no-separate`**: o próprio áudio de entrada é o stem do instrumento pedido. Exige
   exatamente um instrumento em `--instruments`. É açúcar para `--stem <inst>=<entrada>`.
3. **Quando todo instrumento pedido tem stem, o Demucs não roda.** Um `separate_fn` "preparado"
   devolve `SeparationResult(stems={...}, model_version="user-stems")`, usando o ponto de injeção que já
   existe (`separate_fn` em `run_analysis`, `run_transcription` e `run_tablature`). Se só parte dos
   instrumentos tem stem, o Demucs roda e os stems dados substituem os dele.
4. **Análise:** os beats continuam no áudio de entrada (a mistura, ou o próprio stem com
   `--no-separate`). A harmonia soma os stems dados mais o áudio de entrada, quando ele não for um dos
   stems.
5. **Cache:** as versões de `analysis`, `transcription` e `tablature` passam a incluir a identidade dos
   stems dados (instrumento, sha256 do arquivo). Sem `--stem` as versões ficam como estão, e os caches
   atuais continuam válidos.
6. **Worker e desktop:** fora do escopo deste ciclo. O worker só ganha o campo se sair de graça.

## Verificação

- Testes com fakes (sem GPU): o Demucs não é chamado quando todos os stems vêm dados; é chamado no
  caso parcial; a chave do cache muda com stems diferentes e não muda sem `--stem`; `--no-separate`
  com dois instrumentos dá erro de opção (exit 2).
- Probe `scripts/probe_e2e_stems.py`: export real com um stem wav, registrando o tempo de separação
  (≈0) e o `.gp5` gerado, que relê com PyGuitarPro.
