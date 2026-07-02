# Canonical Dataset Schema

## 1. Objetivo

Este documento define o formato canónico utilizado pela framework para
representar cada exemplo do dataset.

O schema canónico é independente de qualquer ferramenta de fine-tuning
(Unsloth, Hugging Face, Llama Factory, Axolotl, OpenAI, etc.).

Todas as integrações futuras deverão ser obtidas através de exportadores
específicos, mantendo este formato como única fonte de verdade.

------------------------------------------------------------------------

## 2. Princípios

O schema deverá:

-   ser independente da ferramenta de treino;
-   representar completamente um exemplo;
-   servir simultaneamente para geração, treino e benchmark;
-   permitir evolução sem quebrar compatibilidade.

------------------------------------------------------------------------

## 3. Estrutura Canónica

Cada exemplo é composto pelos seguintes blocos:

``` text
Example
│
├── Metadata
├── Context
├── Task
├── Expected Behaviour
├── Expected Output
└── Ground Truth
```

------------------------------------------------------------------------

## 4. Blocos

### 4.1 Metadata

Contém informação técnica utilizada pela framework.

Campos sugeridos:

-   id
-   version
-   domain
-   language
-   source
-   operations
-   complexity
-   conversation_length
-   created_at

------------------------------------------------------------------------

### 4.2 Context

Representa toda a informação disponível para o modelo.

Nesta primeira versão será texto, mas o schema deverá permitir futura
extensão para tabelas, imagens ou outros formatos.

------------------------------------------------------------------------

### 4.3 Task

Define o que o modelo deverá executar.

Uma tarefa pode ser:

-   responder;
-   resumir;
-   validar;
-   comparar;
-   extrair informação;
-   estruturar informação;
-   reformular;
-   qualquer outra operação definida pela framework.

A tarefa pode ainda conter restrições, como idioma, formato ou tamanho
da resposta.

------------------------------------------------------------------------

### 4.4 Expected Behaviour

Descreve o comportamento esperado antes da resposta.

Campos principais:

-   expected_decision (D1, D2 ou D3)
-   expected_operation (Ox.y)

Este bloco representa o comportamento que pretendemos ensinar ao modelo.

------------------------------------------------------------------------

### 4.5 Expected Output

Define o resultado esperado.

Exemplos:

-   resposta final;
-   pedido de mais contexto;
-   recusa fundamentada.

------------------------------------------------------------------------

### 4.6 Ground Truth

Contém a informação utilizada para validar o comportamento do modelo.

Pode incluir:

-   factos de suporte;
-   evidências utilizadas;
-   informação considerada em falta;
-   justificação da decisão;
-   observações.

Este bloco não é destinado ao treino do modelo. Constitui a referência
utilizada pela framework durante a avaliação.

------------------------------------------------------------------------

## 5. Separação entre Dataset e Avaliação

O dataset não contém resultados de avaliação.

O dataset contém apenas a verdade de referência (Ground Truth).

Após a execução de um modelo, a framework produzirá um objeto
independente contendo:

-   resposta produzida;
-   decisão tomada;
-   operações identificadas;
-   métricas;
-   comparação com o Ground Truth.

Esta separação permite utilizar o mesmo dataset para:

-   fine-tuning;
-   benchmark;
-   comparação entre modelos;
-   comparação entre prompts;
-   comparação entre estratégias de recuperação de contexto.

------------------------------------------------------------------------

## 6. Compatibilidade

O schema canónico será convertido automaticamente para formatos
específicos através de módulos de exportação.

Exemplos:

-   Hugging Face Datasets
-   Unsloth
-   Llama Factory
-   Axolotl
-   OpenAI Fine-tuning

Desta forma, a evolução das ferramentas não implica alterações ao modelo
de dados da framework.

------------------------------------------------------------------------

## 7. Evolução

Novos campos poderão ser adicionados mantendo compatibilidade
retroativa.

O schema canónico deverá permanecer a única representação oficial dos
exemplos do dataset.
