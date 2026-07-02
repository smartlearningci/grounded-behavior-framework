# Dataset Generation Framework

## 1. Objetivo

Este documento define a arquitetura da framework responsável pela
geração do dataset.

O objetivo não é definir uma pipeline fixa, mas uma arquitetura modular
baseada em interfaces, permitindo utilizar qualquer modelo de IA,
algoritmos determinísticos ou combinações entre ambos.

A framework deverá ser independente dos modelos utilizados.

------------------------------------------------------------------------

## 2. Princípios

A framework deverá obedecer aos seguintes princípios:

-   Independência dos modelos de IA;
-   Arquitetura modular;
-   Baixo acoplamento entre componentes;
-   Elevada reutilização;
-   Possibilidade de substituir qualquer componente sem alterar os
    restantes;
-   Compatibilidade com diferentes fornecedores de IA e modelos locais.

------------------------------------------------------------------------

## 3. Filosofia

Cada etapa da geração do dataset representa um papel (Role) e não um
modelo específico.

A framework conhece apenas interfaces.

As implementações concretas podem utilizar:

-   ChatGPT
-   Claude
-   Gemini
-   Grok
-   Mistral
-   Copilot
-   Qwen
-   Gemma
-   Modelos locais
-   Algoritmos Python

ou qualquer combinação entre eles.

------------------------------------------------------------------------

## 4. Arquitetura Geral

``` text
Fonte Documental
        │
        ▼
Document Loader
        │
        ▼
Context Builder
        │
        ▼
Task Generator
        │
        ▼
Decision Generator
        │
        ▼
Operation Classifier
        │
        ▼
Complexity Classifier
        │
        ▼
Ground Truth Generator
        │
        ▼
Validator
        │
        ▼
Canonical Dataset
        │
        ▼
Exporters
```

------------------------------------------------------------------------

## 5. Interfaces da Framework

  Interface              Responsabilidade
  ---------------------- ----------------------------------------------------
  DocumentLoader         Carregar documentos de origem.
  ContextBuilder         Construir contextos a partir dos documentos.
  TaskGenerator          Gerar tarefas sobre o contexto.
  DecisionGenerator      Determinar a decisão esperada (D1, D2 ou D3).
  OperationClassifier    Classificar as operações (O).
  ComplexityClassifier   Classificar a complexidade (C).
  GroundTruthGenerator   Gerar a resposta e as evidências esperadas.
  Validator              Validar a qualidade dos exemplos.
  Exporter               Converter o dataset canónico para outros formatos.

------------------------------------------------------------------------

## 6. Implementações

Cada interface poderá possuir várias implementações.

Exemplos:

-   GPTTaskGenerator
-   ClaudeTaskGenerator
-   GeminiTaskGenerator
-   LocalQwenTaskGenerator
-   PythonRuleTaskGenerator

Todas deverão produzir exatamente o mesmo schema canónico.

------------------------------------------------------------------------

## 7. Polimorfismo

A framework aplica os princípios clássicos de Engenharia de Software.

Cada componente trabalha sobre uma interface e não sobre uma
implementação concreta.

Desta forma é possível substituir um fornecedor de IA por outro sem
alterar o restante sistema.

Exemplo:

TaskGenerator

↓

Claude

ou

↓

ChatGPT

ou

↓

Gemini

ou

↓

Modelo Local

------------------------------------------------------------------------

## 8. Fluxos Possíveis

A framework deverá suportar diferentes estratégias de geração.

Exemplos:

-   Um único modelo executa todas as etapas.
-   Um modelo diferente para cada interface.
-   Combinação entre IA e regras determinísticas.
-   Execução distribuída entre vários fornecedores.

------------------------------------------------------------------------

## 9. Objetivos de Investigação

Esta arquitetura permitirá estudar questões como:

-   Que modelo gera melhores tarefas?
-   Que modelo produz melhores Ground Truth?
-   É possível substituir modelos comerciais por modelos locais?
-   Qual a melhor combinação de modelos para gerar datasets de elevada
    qualidade?

------------------------------------------------------------------------

## 10. Evolução

Novas interfaces poderão ser adicionadas mantendo compatibilidade com a
arquitetura.

Novos fornecedores de IA poderão ser integrados apenas através da
implementação das interfaces existentes.

O schema canónico permanece o ponto central de toda a framework.
