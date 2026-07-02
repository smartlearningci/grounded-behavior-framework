# Dataset Specification

## 1. Objetivo

O objetivo deste dataset não é ensinar conhecimento factual ao modelo,
mas sim ensinar um **comportamento**.

Pretende-se desenvolver um dataset que permita treinar Small Language
Models (SLMs) para executarem tarefas utilizando **exclusivamente** a
informação fornecida num contexto, independentemente do domínio do
conhecimento.

O foco do projeto é o desenvolvimento de uma metodologia reutilizável de
construção de datasets comportamentais, capaz de ser aplicada a
diferentes áreas (turismo, história, ciência, tecnologia, medicina,
legislação, documentação técnica, entre outras).

O conhecimento contido no contexto é sempre considerado a única fonte de
verdade durante a execução da tarefa.

------------------------------------------------------------------------

## 2. Princípio Central

O projeto baseia-se no conceito de **Grounded Behaviour**.

O modelo deve aprender que qualquer resposta depende apenas do contexto
recebido e nunca do conhecimento memorizado durante o pré-treino.

Os princípios fundamentais são:

-   utilizar exclusivamente a informação presente no contexto;
-   ignorar conhecimento externo durante a execução da tarefa;
-   fundamentar todas as respostas em evidências presentes no contexto;
-   distinguir claramente entre contexto suficiente e contexto
    insuficiente;
-   nunca inventar informação;
-   identificar explicitamente qual a informação em falta quando o
    contexto não permite executar a tarefa.

O objetivo não é produzir respostas corretas "em geral", mas respostas
corretas **relativamente ao contexto fornecido**.

------------------------------------------------------------------------

## 3. Modelo de Funcionamento

Todos os exemplos do dataset seguem o mesmo modelo conceptual.

``` text
CONTEXTO
        ↓
TAREFA
        ↓
AVALIAÇÃO DA SUFICIÊNCIA DO CONTEXTO
        ↓
┌───────────────────────┐
│ Contexto suficiente?  │
└───────────┬───────────┘
            │
     Sim    │    Não
            │
            ▼
Executar     Identificar informação em falta
a tarefa     e solicitar novo contexto
```

O contexto representa toda a informação disponível para o modelo.

A tarefa pode assumir diferentes formas (responder, resumir, validar,
comparar, extrair informação, etc.), mas o processo de decisão mantém-se
inalterado.

------------------------------------------------------------------------

## 4. Filosofia do Dataset

O dataset pretende ensinar duas competências distintas:

### 4.1 Decisão

Antes de responder, o modelo deve decidir se possui contexto suficiente
para executar a tarefa.

### 4.2 Execução

Quando existir contexto suficiente, o modelo deverá executar
corretamente a tarefa utilizando apenas a informação disponível.

Esta separação entre **decidir** e **executar** constitui um dos
princípios fundamentais da framework.

------------------------------------------------------------------------

## 5. Estrutura Geral dos Exemplos

Cada exemplo do dataset deverá conter, de forma explícita ou implícita:

-   contexto;
-   tarefa;
-   resposta esperada;
-   decisão esperada relativamente à suficiência do contexto.

Em versões futuras poderão ser incluídos metadados adicionais (operação,
domínio, dificuldade, origem do texto, etc.).

------------------------------------------------------------------------

## 6. Regras Gerais

Todas as respostas produzidas durante o treino deverão obedecer às
seguintes regras:

-   utilizar exclusivamente informação presente no contexto;
-   não utilizar conhecimento externo;
-   não completar lacunas com inferências não suportadas;
-   não inventar entidades, datas ou factos;
-   corrigir afirmações incorretas quando existirem evidências no
    contexto;
-   reconhecer explicitamente quando o contexto é insuficiente;
-   indicar, sempre que possível, que informação adicional seria
    necessária para concluir a tarefa;
-   utilizar linguagem clara, objetiva e consistente.

------------------------------------------------------------------------

## 7. Critérios de Qualidade

Cada exemplo do dataset deverá cumprir os seguintes critérios:

-   fidelidade integral ao contexto;
-   ausência de alucinações;
-   coerência entre contexto, tarefa e resposta;
-   diversidade de domínios;
-   diversidade de níveis de dificuldade;
-   possibilidade de validação automática;
-   reutilização da mesma metodologia em qualquer domínio.

O objetivo é maximizar a qualidade do comportamento aprendido e não a
quantidade de conhecimento presente no dataset.

------------------------------------------------------------------------

## 8. Escalabilidade

O desenvolvimento do dataset será incremental.

Fases previstas:

1.  Definição da metodologia.
2.  Dataset piloto (\~500 exemplos).
3.  Avaliação do comportamento aprendido.
4.  Primeira versão (\~10 000 exemplos).
5.  Expansão contínua para novos domínios.

A framework deverá permitir gerar novos datasets mantendo a mesma
filosofia, alterando apenas os documentos de origem.
