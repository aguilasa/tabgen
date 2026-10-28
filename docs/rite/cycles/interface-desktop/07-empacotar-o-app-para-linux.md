---
id: UI-TASK-07
---

# UI-TASK-07 — Empacotar o app para Linux

## Goal

O app empacota para Linux: `tauri build` gera .deb e AppImage que instalam/rodam numa máquina
com o tabgen instalado em venv; o app embala só o frontend + binário Tauri e localiza o Python
como no dev (preferências), com a tela Ambiente orientando quando faltar algo. README do
`desktop/` documenta build e requisitos.

## Escopo

- In: configuração de bundle do Tauri (ícone, nome, versão); verificação do fluxo
  "Python ausente → orientação"; `desktop/README.md` (build, requisitos, onde configurar o
  Python); entrada no README raiz apontando para o app.
- Out: CI; instaladores Windows/macOS; bundling do Python (fora da v1).

## Done criteria

- [ ] `cd desktop && npm run tauri build` sai 0 e gera `.deb` e `.AppImage` (caminhos e tamanhos
      nas Notes com o comando).
- [ ] AppImage roda nesta máquina: abre, Ambiente verde, pipeline da amostra funciona
      (screenshot nas Notes).
- [ ] Com preferência de Python apontando para caminho inexistente, o AppImage abre e orienta em
      vez de quebrar.
- [ ] `desktop/README.md` existe com build + requisitos; README raiz linka.

## Notes

Tamanho do bundle e tempo de build vão nas Notes com os comandos (regra do CLAUDE.md sobre
números).

## Execution Log
