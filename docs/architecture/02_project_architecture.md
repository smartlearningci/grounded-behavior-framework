# Project Architecture

## 1. Objetivo

Definir a organização técnica do projeto e o papel de cada componente.

## 2. Componentes principais

- VSCode: desenvolvimento local.
- GitHub: versionamento de código, documentação, prompts e notebooks.
- Google Colab: execução de notebooks e treino.
- Google Drive: armazenamento de datasets, modelos, checkpoints e resultados.
- Hugging Face: publicação de datasets e modelos.

## 3. Estrutura de pastas

- docs/
- prompts/
- notebooks/
- src/
- datasets/
- experiments/
- reports/
- tests/

## 4. Fluxo de trabalho

VSCode → GitHub → Colab → Google Drive / Hugging Face

## 5. Regras

- Código e documentação ficam no GitHub.
- Ficheiros grandes ficam na Google Drive.
- Modelos e datasets finais podem ser publicados no Hugging Face.
- Notebooks devem orquestrar código, não concentrar toda a lógica.

## 6. Próximos passos

Após esta arquitetura, será definida a especificação do dataset.