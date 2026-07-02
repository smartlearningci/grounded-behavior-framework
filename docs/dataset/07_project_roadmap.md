# Project Roadmap

## Objetivo

Este documento descreve o plano de evolução da framework, desde a
definição da arquitetura até à validação experimental dos modelos.

O roadmap é um documento vivo e deverá ser atualizado à medida que o
projeto evolui.

------------------------------------------------------------------------

# Fase 1 --- Arquitetura

## Objetivo

Definir a arquitetura conceptual da framework.

### Entregáveis

-   [x] Project Vision
-   [x] Project Architecture
-   [x] Dataset Specification
-   [x] Context Decision Model
-   [x] Context Operations
-   [x] Complexity Model
-   [x] Canonical Dataset Schema
-   [x] Dataset Generation Framework

**Estado:** Concluída

------------------------------------------------------------------------

# Fase 2 --- Core Framework

## Objetivo

Implementar o núcleo da framework.

### Entregáveis

-   [ ] Estrutura do projeto (`src/`)
-   [ ] Modelo canónico do dataset
-   [ ] Interfaces (ABCs)
-   [ ] Constantes e enums
-   [ ] Configuração
-   [ ] Logging
-   [ ] Gestão de ficheiros
-   [ ] Testes unitários do núcleo

**Estado:** Não iniciada

------------------------------------------------------------------------

# Fase 3 --- Providers

## Objetivo

Implementar os fornecedores de IA.

### Possíveis Providers

-   [ ] OpenAI
-   [ ] Anthropic
-   [ ] Google Gemini
-   [ ] xAI Grok
-   [ ] Mistral AI
-   [ ] Ollama
-   [ ] LM Studio
-   [ ] OpenRouter
-   [ ] Python (regras determinísticas)

Todos deverão implementar as mesmas interfaces.

**Estado:** Não iniciada

------------------------------------------------------------------------

# Fase 4 --- Dataset Generation

## Objetivo

Construir automaticamente datasets comportamentais.

### Entregáveis

-   [ ] Document Loader
-   [ ] Context Builder
-   [ ] Task Generator
-   [ ] Decision Generator
-   [ ] Operation Classifier
-   [ ] Complexity Classifier
-   [ ] Ground Truth Generator
-   [ ] Validator

**Estado:** Não iniciada

------------------------------------------------------------------------

# Fase 5 --- Exportação

## Objetivo

Converter o schema canónico para diferentes formatos.

### Exportadores

-   [ ] Hugging Face Dataset
-   [ ] Unsloth
-   [ ] Llama Factory
-   [ ] Axolotl
-   [ ] OpenAI Fine-tuning

**Estado:** Não iniciada

------------------------------------------------------------------------

# Fase 6 --- Fine-tuning

## Objetivo

Treinar e comparar Small Language Models.

### Entregáveis

-   [ ] Pipeline de treino
-   [ ] Gestão de checkpoints
-   [ ] Publicação de modelos
-   [ ] Testes funcionais

**Estado:** Não iniciada

------------------------------------------------------------------------

# Fase 7 --- Benchmark

## Objetivo

Avaliar modelos e estratégias.

### Comparações previstas

-   [ ] Modelo vs Modelo
-   [ ] Prompt vs Prompt
-   [ ] Fine-tuning vs Base
-   [ ] RAG vs Fine-tuning
-   [ ] Providers de IA
-   [ ] Estratégias de geração de dataset

**Estado:** Não iniciada

------------------------------------------------------------------------

# Fase 8 --- Casos de Estudo

## Objetivo

Validar a framework em diferentes domínios.

### Casos previstos

-   [ ] Torre de Belém
-   [ ] Património Cultural
-   [ ] Documentação Técnica
-   [ ] Saúde
-   [ ] Legislação
-   [ ] Educação

**Estado:** Não iniciada

------------------------------------------------------------------------

# Fase 9 --- Publicação

## Objetivo

Disponibilizar a framework.

### Entregáveis

-   [ ] Documentação completa
-   [ ] Repositório GitHub
-   [ ] Datasets públicos
-   [ ] Modelos publicados
-   [ ] Artigo científico
-   [ ] Demonstrações

**Estado:** Não iniciada

------------------------------------------------------------------------

# Visão Geral

  Fase   Nome                 Estado
  ------ -------------------- --------
  1      Arquitetura          ✅
  2      Core Framework       ⬜
  3      Providers            ⬜
  4      Dataset Generation   ⬜
  5      Exportação           ⬜
  6      Fine-tuning          ⬜
  7      Benchmark            ⬜
  8      Casos de Estudo      ⬜
  9      Publicação           ⬜

------------------------------------------------------------------------

## Nota

O desenvolvimento deverá ser incremental. Cada fase só deverá avançar
quando a anterior estiver suficientemente estabilizada, garantindo uma
arquitetura consistente e facilmente extensível.
