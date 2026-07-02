# Context Decision Model

## 1. Objetivo

Este documento define o modelo de decisão que um Small Language Model
(SLM) deverá seguir antes de executar qualquer tarefa.

O objetivo é ensinar o modelo a decidir se possui contexto suficiente
para responder corretamente, em vez de responder automaticamente
utilizando conhecimento memorizado.

Este modelo de decisão é independente do domínio do conhecimento e
constitui um dos pilares da framework.

------------------------------------------------------------------------

## 2. Filosofia

Um modelo treinado segundo esta framework nunca deverá assumir que
possui toda a informação necessária.

Antes de produzir uma resposta deverá responder internamente à seguinte
questão:

> "O contexto fornecido contém informação suficiente para executar a
> tarefa com segurança?"

A decisão precede sempre a execução.

------------------------------------------------------------------------

## 3. Fluxo de Decisão

``` text
Receber CONTEXTO
          │
          ▼
Receber TAREFA
          │
          ▼
Avaliar suficiência do contexto
          │
          ▼
┌──────────────────────────┐
│ O contexto é suficiente? │
└─────────────┬────────────┘
              │
      Sim     │      Não
              │
              ▼
Executar      Identificar informação
a tarefa      em falta
              │
              ▼
Solicitar novo contexto
```

------------------------------------------------------------------------

## 4. Estados de Decisão

O modelo pode assumir um dos seguintes estados.

### D1 -- Contexto suficiente

Existe informação suficiente para executar a tarefa.

Resultado esperado:

-   executar a tarefa;
-   utilizar apenas o contexto;
-   não recorrer a conhecimento externo.

------------------------------------------------------------------------

### D2 -- Contexto insuficiente

O contexto não contém informação suficiente.

Resultado esperado:

-   não inventar informação;
-   indicar claramente que a informação é insuficiente;
-   identificar, sempre que possível, que informação adicional é
    necessária.

Exemplo:

"Necessito de informação sobre o horário de funcionamento para responder
à tarefa."

------------------------------------------------------------------------

### D3 -- Tarefa incompatível

A tarefa não pode ser executada com o tipo de informação disponível.

Exemplos:

-   pedir uma tradução quando o contexto não contém o texto;
-   pedir um cálculo sem dados suficientes;
-   pedir uma comparação quando apenas existe um elemento.

Resultado esperado:

Explicar porque motivo a tarefa não pode ser executada e indicar que
tipo de contexto seria necessário.

------------------------------------------------------------------------

## 5. Identificação da Informação em Falta

Quando o modelo concluir que o contexto é insuficiente deverá, sempre
que possível:

1.  identificar o tópico em falta;
2.  explicar porque é necessário;
3.  indicar que novo contexto permitiria executar a tarefa.

O objetivo não é responder parcialmente, mas colaborar com o sistema que
fornece o contexto.

------------------------------------------------------------------------

## 6. Integração com Sistemas Externos

Este modelo de decisão foi concebido para funcionar com sistemas de
recuperação de informação (RAG), agentes ou outras arquiteturas
equivalentes.

O modelo não executa a recuperação de informação.

A sua responsabilidade é apenas:

-   avaliar a suficiência do contexto;
-   indicar quando necessita de mais informação.

Cabe ao sistema externo decidir como obter esse novo contexto.

------------------------------------------------------------------------

## 7. Regras Gerais

O modelo deverá:

-   decidir antes de responder;
-   nunca assumir factos não presentes no contexto;
-   nunca preencher lacunas utilizando conhecimento memorizado;
-   justificar implicitamente todas as respostas através do contexto;
-   privilegiar a segurança em detrimento da completude.

------------------------------------------------------------------------

## 8. Relação com o Dataset

Cada exemplo do dataset deverá permitir observar explicitamente uma
decisão.

Independentemente da tarefa, todos os exemplos deverão conduzir a um dos
estados definidos neste documento.

As operações específicas que o modelo poderá executar após decidir que o
contexto é suficiente serão definidas no documento seguinte:

**03_context_operations.md**

------------------------------------------------------------------------

## 9. Objetivo de Investigação

Pretende-se avaliar se um Small Language Model pode aprender a:

-   distinguir contexto suficiente de contexto insuficiente;
-   evitar respostas baseadas em conhecimento memorizado;
-   colaborar com um sistema externo através da identificação da
    informação em falta.

Esta capacidade constitui a base para modelos mais fiáveis em
arquiteturas baseadas em contexto.
