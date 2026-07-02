# Context Operations

## 1. Objetivo

Este documento define as operações que um Small Language Model deverá
ser capaz de executar **após concluir que o contexto fornecido é
suficiente**.

As operações descritas são independentes do domínio (turismo, medicina,
ciência, legislação, etc.) e representam capacidades reutilizáveis da
framework.

Este documento complementa o **02_context_decision_model.md**.

------------------------------------------------------------------------

## 2. Princípios

Todas as operações devem obedecer às seguintes regras:

-   utilizar exclusivamente a informação presente no contexto;
-   não recorrer a conhecimento externo;
-   manter fidelidade ao contexto;
-   justificar implicitamente todas as respostas através da informação
    disponível.

------------------------------------------------------------------------

# O1 -- Localizar Informação

## Objetivo

Encontrar informação explicitamente presente no contexto.

### Suboperações

  ------------------------------------------------------------------------
  ID          Operação                     Descrição
  ----------- ---------------------------- -------------------------------
  O1.1        Identificar entidades        Pessoas, locais, organizações,
                                           objetos.

  O1.2        Identificar valores          Datas, horas, quantidades,
                                           preços, medidas.

  O1.3        Identificar factos           Localizar afirmações
                                           explícitas.

  O1.4        Identificar relações         Relações descritas diretamente
              explícitas                   no texto.
  ------------------------------------------------------------------------

------------------------------------------------------------------------

# O2 -- Compreender Informação

## Objetivo

Interpretar corretamente o significado da informação presente no
contexto.

### Suboperações

  ------------------------------------------------------------------------
  ID          Operação                     Descrição
  ----------- ---------------------------- -------------------------------
  O2.1        Explicar                     Explicar um conceito presente
                                           no contexto.

  O2.2        Interpretar                  Inferir o significado de
                                           expressões explícitas.

  O2.3        Classificar                  Classificar elementos segundo
                                           critérios do contexto.

  O2.4        Comparar                     Comparar elementos utilizando
                                           apenas o contexto.
  ------------------------------------------------------------------------

------------------------------------------------------------------------

# O3 -- Relacionar Informação

## Objetivo

Combinar diferentes partes do contexto para produzir uma resposta.

### Suboperações

  ------------------------------------------------------------------------
  ID          Operação                     Descrição
  ----------- ---------------------------- -------------------------------
  O3.1        Integrar factos              Combinar dois ou mais factos.

  O3.2        Relacionar entidades         Estabelecer relações entre
                                           elementos.

  O3.3        Ordenar                      Organizar informação
                                           cronológica ou logicamente.

  O3.4        Identificar dependências     Relações de causa, consequência
                                           ou pertença quando explícitas.
  ------------------------------------------------------------------------

------------------------------------------------------------------------

# O4 -- Validar Informação

## Objetivo

Avaliar afirmações utilizando exclusivamente o contexto.

### Suboperações

  ------------------------------------------------------------------------
  ID          Operação                     Descrição
  ----------- ---------------------------- -------------------------------
  O4.1        Confirmar                    Confirmar afirmações.

  O4.2        Refutar                      Corrigir afirmações incorretas.

  O4.3        Justificar                   Fundamentar respostas com
                                           evidências do contexto.

  O4.4        Detetar inconsistências      Identificar contradições
                                           existentes no contexto.
  ------------------------------------------------------------------------

------------------------------------------------------------------------

# O5 -- Transformar Informação

## Objetivo

Alterar a forma de apresentação da informação sem alterar o seu
significado.

### Suboperações

  ID     Operação      Descrição
  ------ ------------- ------------------------------------------------
  O5.1   Resumir       Produzir um resumo fiel.
  O5.2   Reformular    Reescrever mantendo o significado.
  O5.3   Simplificar   Adaptar a linguagem ao destinatário.
  O5.4   Estruturar    Converter em listas, tabelas ou tópicos.
  O5.5   Extrair       Extrair apenas determinado tipo de informação.

------------------------------------------------------------------------

# O6 -- Restringir a Resposta

## Objetivo

Cumprir restrições impostas pela tarefa relativamente ao formato da
resposta.

### Suboperações

  ------------------------------------------------------------------------
  ID          Operação                     Descrição
  ----------- ---------------------------- -------------------------------
  O6.1        Limitar extensão             Número de palavras, frases ou
                                           caracteres.

  O6.2        Controlar formato            JSON, lista, tabela, texto
                                           simples, etc.

  O6.3        Controlar idioma             Produzir a resposta na língua
                                           indicada.

  O6.4        Resposta fechada             Sim/Não, verdadeiro/falso ou
                                           opções definidas.
  ------------------------------------------------------------------------

------------------------------------------------------------------------

# O7 -- Executar Instruções sobre o Contexto

## Objetivo

Executar instruções específicas de processamento utilizando apenas o
contexto disponível.

### Suboperações

  ------------------------------------------------------------------------
  ID          Operação                     Descrição
  ----------- ---------------------------- -------------------------------
  O7.1        Selecionar secções           Utilizar apenas parte do
                                           contexto.

  O7.2        Ignorar informação           Desconsiderar informação
                                           irrelevante indicada na tarefa.

  O7.3        Aplicar regras               Executar regras explícitas
                                           fornecidas na tarefa.

  O7.4        Combinar instruções          Cumprir múltiplas instruções
                                           simultaneamente.
  ------------------------------------------------------------------------

------------------------------------------------------------------------

## 3. Observações

-   Um exemplo do dataset pode envolver uma ou mais operações.
-   As operações são independentes do domínio.
-   A decisão sobre a suficiência do contexto é tratada exclusivamente
    no documento **02_context_decision_model.md**.
-   Conversações de múltiplos turnos não constituem uma operação;
    representam apenas um formato de interação que pode combinar
    diferentes operações.
