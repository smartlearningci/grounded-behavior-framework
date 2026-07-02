# Complexity Model

## 1. Objetivo

Este documento define uma escala de complexidade independente das
operações do contexto.

O objetivo é classificar a dificuldade cognitiva de cada exemplo do
dataset, permitindo construir conjuntos de treino equilibrados e
comparar o desempenho de diferentes modelos.

A complexidade é uma dimensão independente das operações definidas em
**03_context_operations.md**.

------------------------------------------------------------------------

## 2. Princípios

A complexidade depende da quantidade de processamento exigido ao modelo
e não do domínio do conhecimento.

A mesma operação pode existir em diferentes níveis de complexidade.

Exemplos:

-   O1.1 + C1 → Identificar uma data.
-   O1.1 + C3 → Identificar uma entidade entre vários candidatos.
-   O3.2 + C5 → Relacionar múltiplas entidades distribuídas por um
    contexto longo.

------------------------------------------------------------------------

## 3. Escala de Complexidade

  -----------------------------------------------------------------------
  Nível                   Nome                    Características
  ----------------------- ----------------------- -----------------------
  C1                      Muito Baixa             Um único facto
                                                  explícito.

  C2                      Baixa                   Dois ou mais factos
                                                  explícitos.

  C3                      Média                   Combinação de
                                                  informação distribuída
                                                  pelo contexto.

  C4                      Elevada                 Múltiplas operações e
                                                  restrições.

  C5                      Muito Elevada           Contextos longos,
                                                  várias dependências e
                                                  decisões sucessivas.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 4. Critérios de Avaliação

A complexidade deverá considerar:

-   comprimento do contexto;
-   número de factos relevantes;
-   número de operações necessárias;
-   quantidade de restrições da tarefa;
-   número de passos de raciocínio suportados pelo contexto.

------------------------------------------------------------------------

## 5. Exemplos

### C1

Uma única pergunta baseada num único facto explícito.

### C2

Uma pergunta envolvendo dois factos explícitos.

### C3

Necessidade de integrar informação distribuída.

### C4

Combinação de várias operações respeitando restrições.

### C5

Contexto extenso com múltiplas operações e instruções.

------------------------------------------------------------------------

## 6. Utilização no Dataset

Cada exemplo deverá possuir pelo menos:

-   Operação (Ox.y)
-   Complexidade (Cx)

Exemplo:

  Campo          Valor
  -------------- -------
  Operação       O3.2
  Complexidade   C3

Esta classificação permitirá analisar os modelos por tipo de operação e
por nível de dificuldade.

------------------------------------------------------------------------

## 7. Evolução

A escala poderá ser refinada no futuro mantendo compatibilidade com os
datasets já produzidos.
