# Grounded Behavior Framework

O **Grounded Behavior Framework** é um projeto de investigação e engenharia
orientado ao treino e à avaliação de **Small Language Models (SLMs)**. A questão
central é saber se um modelo pequeno pode adquirir capacidades cognitivas
definidas progressivamente através de um currículo cuidadosamente estruturado,
em vez de se limitar a memorizar conteúdo de um domínio.

O conteúdo de domínio — por exemplo, bibliotecas, turismo, ciência ou
documentação técnica — é usado como veículo para treinar e testar operações
cognitivas. A fonte de verdade de cada tarefa é o contexto fornecido. O modelo
deve decidir se esse contexto é suficiente, executar apenas operações suportadas
por ele e evitar completar lacunas com conhecimento externo.

> **Âmbito deste documento:** o README descreve os ficheiros mantidos no
> repositório e distingue componentes implementados, validações experimentais e
> trabalho planeado. Ausência de evidência é assinalada como **Por confirmar**.
> Os documentos de arquitetura continuam a ser a base conceptual; o software
> atual implementa apenas uma parte do fluxo pretendido.

## Índice

1. [Motivação da investigação](#1-motivação-da-investigação)
2. [Principais questões de investigação](#2-principais-questões-de-investigação)
3. [Currículo cognitivo atual](#3-currículo-cognitivo-atual)
4. [Progresso experimental](#4-progresso-experimental)
5. [Estado atual do projeto](#5-estado-atual-do-projeto)
6. [Visão geral da arquitetura](#6-visão-geral-da-arquitetura)
7. [Estrutura do repositório](#7-estrutura-do-repositório)
8. [Classes e interfaces principais](#8-classes-e-interfaces-principais)
9. [Packages e dependências](#9-packages-e-dependências)
10. [Artefactos e formatos de dados](#10-artefactos-e-formatos-de-dados)
11. [Validação de providers](#11-validação-de-providers)
12. [Suite de testes](#12-suite-de-testes)
13. [O que são mocks](#13-o-que-são-mocks)
14. [Como funcionam os mocks existentes](#14-como-funcionam-os-mocks-existentes)
15. [Como passar de mocks para testes reais](#15-como-passar-de-mocks-para-testes-reais)
16. [Variáveis de ambiente e secrets](#16-variáveis-de-ambiente-e-secrets)
17. [Executar o projeto](#17-executar-o-projeto)
18. [Fluxo de geração do dataset](#18-fluxo-de-geração-do-dataset)
19. [Rastreabilidade](#19-rastreabilidade)
20. [Outputs finais](#20-outputs-finais)
21. [Limitações](#21-limitações)
22. [Roadmap](#22-roadmap)
23. [Checklist de reprodutibilidade](#23-checklist-de-reprodutibilidade)
24. [Regras de contribuição e segurança](#24-regras-de-contribuição-e-segurança)
25. [Guia de navegação](#25-guia-de-navegação)

## 1. Motivação da investigação

Os SLMs são interessantes para execução local, privacidade, menor custo e menor
latência, mas têm capacidade limitada e podem responder incorretamente quando a
tarefa excede a informação disponível. A visão científica, descrita em
[`docs/architecture/01_project_vision.md`](docs/architecture/01_project_vision.md),
é desenvolver uma metodologia reutilizável para ensinar comportamento grounded:
responder exclusivamente com base no contexto, reconhecer insuficiência e não
inventar informação.

A hipótese de trabalho é que um SLM pode melhorar a generalização para situações
novas quando aprende através de um currículo progressivo composto por
capacidades e subskills explicitamente definidos. A analogia com aprendizagem
humana é metodológica:

- a aprendizagem é progressiva;
- capacidades elementares suportam capacidades posteriores mais complexas;
- pessoas e modelos têm limites inerentes diferentes;
- não se afirma que redes neuronais e cérebros humanos sejam biologicamente
  equivalentes;
- testa-se se uma progressão estruturada melhora o comportamento observável do
  modelo.

Nesta abordagem, aumentar exemplos ou epochs não é suficiente por si só. A
qualidade semântica dos exemplos, a estrutura cognitiva, a diversidade de
formulações e domínios e a cobertura sistemática das combinações relevantes são
tratadas como variáveis de investigação. Um dataset maior mas redundante pode
reforçar padrões superficiais; uma matriz de cobertura bem definida poderá
permitir saber o que foi realmente treinado e testado. A implementação dessa
matriz ainda não existe neste repositório.

O projeto não pretende construir uma aplicação final nem um sistema RAG
completo. Sistemas RAG, agentes e outros recuperadores de contexto são potenciais
casos de estudo; a responsabilidade do modelo aqui é avaliar e usar o contexto,
não recuperá-lo. Esta separação está descrita em
[`docs/dataset/02_context_decision_model.md`](docs/dataset/02_context_decision_model.md).

## 2. Principais questões de investigação

As questões seguintes são coerentes com a visão e com os artefactos atuais, mas
a maioria ainda não tem resposta experimental armazenada no repositório:

- Pode um modelo de linguagem muito pequeno adquirir uma capacidade elementar
  claramente definida?
- A capacidade generaliza para domínios, entidades, formulações e estilos de
  documento não vistos no treino?
- O fine-tuning melhora capacidades ausentes ou frágeis no modelo base?
- O fine-tuning pode causar regressões em comportamentos anteriormente corretos?
- Que operações e subskills evoluem mais e quais parecem limitados pela
  capacidade do modelo?
- Um dataset gerado por vários LLMs aumenta a diversidade linguística e
  estrutural face a um único gerador?
- Uma matriz de cobertura permite construir e reproduzir um currículo cognitivo
  de forma auditável?
- Melhor cobertura do dataset é mais eficaz do que aumentar simplesmente os
  training steps?
- Um SLM aprende a distinguir `D1`, `D2` e `D3` e a identificar a informação em
  falta sem recorrer a conhecimento memorizado?

Não existem ainda benchmarks ou resultados versionados que respondam
quantitativamente a estas perguntas.

## 3. Currículo cognitivo atual

### 3.1 Taxonomia formal confirmada

O currículo atualmente confirmado no código e na documentação é composto por
três dimensões:

| Dimensão | Códigos | Objetivo | Fonte |
|---|---|---|---|
| Decisão | `D1`, `D2`, `D3` | Distinguir contexto suficiente, insuficiente e tarefa incompatível | [`src/core/constants.py`](src/core/constants.py), [`docs/dataset/02_context_decision_model.md`](docs/dataset/02_context_decision_model.md) |
| Operação | `O1`–`O7` | Localizar, compreender, relacionar, validar, transformar, restringir a resposta e executar instruções | [`src/core/constants.py`](src/core/constants.py), [`docs/dataset/03_context_operations.md`](docs/dataset/03_context_operations.md) |
| Complexidade | `C1`–`C5` | Classificar dificuldade de muito baixa a muito elevada | [`src/core/constants.py`](src/core/constants.py), [`docs/dataset/04_complexity_model.md`](docs/dataset/04_complexity_model.md) |

As suboperações `O1.1`–`O7.4` estão definidas no documento de operações, mas o
enum `OperationGroup` implementa apenas os grupos de topo `O1`–`O7`.

### 3.2 Estado de N1

Os cinco notebooks em [`notebooks/`](notebooks/) usam a designação **N1** para
um teste equivalente de geração de dois exemplos. O objetivo confirmado do
teste é localizar um facto explícito num contexto: domínio `Bibliotecas`, facto
`Capacidade`, entidade `Biblioteca`, contexto de 3 a 5 frases, facto no fim,
pergunta direta e sem distratores relevantes. O comportamento esperado é
devolver `context`, `question` e `answer`, com uma única resposta correta que
apareça literalmente no contexto.

| Campo | Estado confirmado |
|---|---|
| Código formal | Apenas `N1` nos notebooks; não existe definição formal de subskill no código ou em Markdown versionado |
| Nome | Localização de um facto explícito |
| Objetivo | Produzir exemplos em que a pergunta é respondida por um facto presente no contexto |
| Contexto | Curto, 3–5 frases, domínio Bibliotecas, facto relevante no fim |
| Dificuldade | Conceptualmente próxima de `O1.3` e `C1`, mas a associação formal é **Por confirmar** |
| Distinção | Pergunta direta, um facto, sem distratores relevantes |
| Estado experimental | Teste de dois exemplos executado e registado nos cinco notebooks de validação |

Os códigos esperados na instrução — `N1A_direct_fact`,
`N1B_ignore_irrelevant`, `N1C_select_among_similar`,
`N1D_paraphrased_question` e `N1E_longer_context` — **não aparecem em nenhum
ficheiro mantido no repositório**. Os seus objetivos,
dificuldades e resultados são, portanto, **Por confirmar** e não são
apresentados como currículo implementado.

## 4. Progresso experimental

Não há datas experimentais explícitas. A ordem abaixo segue a numeração dos
notebooks, não uma cronologia cientificamente registada.

### 4.1 Validações de API registadas

| Ordem | Artefacto | Configuração e resultado armazenado | Interpretação e limitação |
|---|---|---|---|
| 1 | [`notebooks/01_test_gemini_api_fixed_prompt.ipynb`](notebooks/01_test_gemini_api_fixed_prompt.ipynb) | `gemini-3.1-flash-lite`, temperature `0.8`; dois exemplos, JSON válido e duas respostas presentes no contexto | Confirma uma chamada real guardada no notebook e o protocolo mínimo N1; não é benchmark de modelo nem dataset versionado |
| 2 | [`notebooks/02_test_groq_api_fixed_prompt.ipynb`](notebooks/02_test_groq_api_fixed_prompt.ipynb) | `llama-3.3-70b-versatile`, temperature `0.8`, `max_tokens=4000`; dois exemplos válidos e grounded | Confirma o SDK Groq neste ensaio; não testa retry, erros nem geração em escala |
| 3 | [`notebooks/03_test_mistral_api_http_fixed_prompt.ipynb`](notebooks/03_test_mistral_api_http_fixed_prompt.ipynb) | HTTP, `mistral-small-latest`, temperature `0.8`, `max_tokens=4000`; dois exemplos válidos e grounded | Confirma o endpoint utilizado; não há fallback ou retry implementado |
| 4 | [`notebooks/04_test_openrouter_free_client_fallback.ipynb`](notebooks/04_test_openrouter_free_client_fallback.ipynb) | O primeiro modelo Qwen recebeu HTTP 429; o fallback `google/gemma-4-26b-a4b-it:free` respondeu e gerou dois exemplos válidos | Valida retry e fallback client-side num caso real; disponibilidade de modelos gratuitos é variável |
| 5 | [`notebooks/05_test_cerebras_api_fixed_prompt.ipynb`](notebooks/05_test_cerebras_api_fixed_prompt.ipynb) | HTTP, `gemma-4-31b`, temperature `0.8`, `max_tokens=4000`; teste “Olá”, dois exemplos válidos e grounded | As células executadas indicam sucesso, mas a nota final ainda diz “Cerebras: em validação”; estado formal **Por confirmar** |

Os cinco notebooks são artefactos mantidos no repositório. Os JSON descarregados
para `/content/...` não são guardados juntamente com eles. Assim, os outputs
embebidos nos notebooks são evidência de smoke tests, não um dataset
experimental completo ou um arquivo dos raw outputs.

O notebook Cerebras regista ainda `xAI/Grok` como retirado do conjunto ativo por
ausência de créditos. Não existe notebook xAI nem provider implementado.

### 4.2 Experiências sem evidência no repositório

Não foram encontrados datasets N1, matriz de cobertura, notebook de fine-tuning,
checkpoints, relatórios, benchmarks, CSV de avaliação ou resumos JSON. Em
particular, estão **Por confirmar**:

- dataset N1 inicial e dataset N1 v3;
- fine-tuning do Gemma 3 270M;
- baseline e avaliação posterior ao fine-tuning;
- benchmark externo e benchmark externo multi-LLM;
- comparação entre 60, 80 e 120 training steps;
- decisão experimental de conservar 80 steps;
- métricas globais, melhorias, regressões e accuracy por subskill.

Não são apresentados números porque não há artefactos locais que os suportem.

## 5. Estado atual do projeto

### Implementado

- Documentação conceptual e roadmap em [`docs/`](docs/).
- Enums `DecisionType`, `ComplexityLevel` e `OperationGroup` em
  [`src/core/constants.py`](src/core/constants.py).
- Dataclasses do schema canónico e serialização `to_dict()` em
  [`src/core/schema.py`](src/core/schema.py).
- Interfaces abstratas das etapas e `AIProvider` em
  [`src/core/interfaces.py`](src/core/interfaces.py).
- Leitura e validação de configuração YAML em
  [`src/core/config.py`](src/core/config.py).
- Caminhos convencionais do projeto em [`src/config.py`](src/config.py).
- Provider manual `ManualProvider` em
  [`src/providers/manual_provider.py`](src/providers/manual_provider.py).
- Configuração manual em
  [`configs/pipeline.manual.yaml`](configs/pipeline.manual.yaml).
- Factory manual em [`src/core/factory.py`](src/core/factory.py), com testes em
  [`tests/test_factory.py`](tests/test_factory.py).
- `GeminiProvider` em
  [`src/providers/gemini_provider.py`](src/providers/gemini_provider.py), com
  testes mockados em
  [`tests/test_gemini_provider.py`](tests/test_gemini_provider.py).
- Testes da configuração em [`tests/test_config.py`](tests/test_config.py).
- Cinco notebooks de validação de APIs em [`notebooks/`](notebooks/).

### Validado experimentalmente

- Carregamento da configuração manual através da suite local.
- Factory manual e `GeminiProvider` através da suite de testes unitários; a API
  Gemini é substituída por mocks nestes testes.
- Smoke tests reais de Gemini, Groq, Mistral e OpenRouter Free registados nos
  notebooks de validação.
- Smoke test Cerebras executado com sucesso nas células; estado final do próprio
  notebook ainda contraditório e, por isso, **Por confirmar**.

### Próximas implementações

- Registar `GeminiProvider` na factory quando a arquitetura estiver preparada
  para selecionar providers API.
- Implementar as classes `GroqProvider`, `MistralProvider`,
  `OpenRouterProvider` e `CerebrasProvider`.
- Criar testes unitários com mocks e smoke tests de integração opcionais para
  cada API.
- Definir e versionar N1, subskills e matriz de cobertura.
- Implementar carregamento documental, construção de contexto, geração de
  tarefas, classificação, ground truth, validação e exportação.
- Construir datasets canónicos e splits de treino, validação, teste e benchmark.
- Criar pipelines/notebooks de fine-tuning e avaliação.

## 6. Visão geral da arquitetura

### 6.1 Workflow científico e operacional

O diagrama distingue o que existe, o que foi ensaiado e o que permanece alvo de
implementação:

```text
Definições D/O/C em docs/ e src/core/constants.py       [IMPLEMENTED]
Definição formal de N1 e subskills                      [PLANNED]
                         ↓
Matriz de cobertura                                     [PLANNED]
                         ↓
Construção parametrizada de prompts                     [PLANNED]
Prompt fixa equivalente nos notebooks                   [VALIDATED]
                         ↓
Geração por provider
 ├── Gemini, notebook                                   [VALIDATED]
 │    └── GeminiProvider em src/providers/              [IMPLEMENTED]
 ├── Groq, notebook                                     [VALIDATED]
 ├── Mistral, notebook                                  [VALIDATED]
 ├── OpenRouter Free, notebook                          [VALIDATED]
 └── Cerebras, execução bem-sucedida/status formal      [VALIDATED/POR CONFIRMAR]
                         ↓
Raw JSON em /content (não guardado no repositório)      [VALIDATED]
                         ↓
Validação estrutural no próprio notebook                [VALIDATED]
Validação cognitiva completa                            [PLANNED]
                         ↓
Exemplos aprovados e revisão humana                     [PLANNED]
                         ↓
Dataset builder                                         [PLANNED]
 ├── train.jsonl
 ├── validation.jsonl
 ├── test.jsonl
 └── benchmark.jsonl
                         ↓
Exportação/formatação Unsloth                           [PLANNED]
                         ↓
Fine-tuning                                             [PLANNED]
                         ↓
Benchmark externo                                       [PLANNED]
                         ↓
Análise por capacidade e regressão                      [PLANNED]
                         ↓
Feedback para a matriz de cobertura                     [PLANNED]
```

### 6.2 Arquitetura de software existente em `src/`

```text
src/core/config.py + configs/pipeline.manual.yaml       [IMPLEMENTED]
                         ↓
src/core/factory.py                                     [IMPLEMENTED]
                         ↓
src/core/interfaces.py
 ├── AIProvider                                         [IMPLEMENTED]
 │    ├── ManualProvider                                [IMPLEMENTED]
 │    ├── GeminiProvider                                [IMPLEMENTED]
 │    └── Groq/Mistral/OpenRouter/Cerebras              [PLANNED; CLASSES ABSENT]
 ├── DocumentLoader                                     [INTERFACE ONLY]
 ├── ContextBuilder                                     [INTERFACE ONLY]
 ├── TaskGenerator                                      [INTERFACE ONLY]
 ├── DecisionGenerator                                  [INTERFACE ONLY]
 ├── OperationClassifier                                [INTERFACE ONLY]
 ├── ComplexityClassifier                               [INTERFACE ONLY]
 ├── GroundTruthGenerator                               [INTERFACE ONLY]
 ├── Validator                                          [INTERFACE ONLY]
 └── Exporter                                           [INTERFACE ONLY]
                         ↓
src/core/schema.py + src/core/constants.py              [IMPLEMENTED DATA MODEL]
```

A factory atual só reconhece `provider: manual`; não regista
`GeminiProvider` e não executa o pipeline. Embora devolva um `ManualProvider`
para cada secção, esse provider implementa `AIProvider`, não cada interface de
role individual. Esta é uma limitação da fase atual, não uma pipeline completa.

## 7. Estrutura do repositório

```text
grounded-behavior-framework/
├── README.md
├── .gitignore
├── requirements.txt
├── configs/
│   ├── README.md
│   └── pipeline.manual.yaml
├── docs/
│   ├── architecture/
│   │   ├── 01_project_vision.md
│   │   └── 02_project_architecture.md
│   └── dataset/
│       ├── 01_dataset_specification.md
│       ├── 02_context_decision_model.md
│       ├── 03_context_operations.md
│       ├── 04_complexity_model.md
│       ├── 05_canonical_dataset_schema.md
│       ├── 06_dataset_generation_framework.md
│       └── 07_project_roadmap.md
├── src/
│   ├── config.py
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── factory.py
│   │   ├── interfaces.py
│   │   └── schema.py
│   └── providers/
│       ├── manual_provider.py
│       └── gemini_provider.py
├── tests/
│   ├── test_config.py
│   ├── test_factory.py
│   └── test_gemini_provider.py
└── notebooks/
    ├── 01_test_gemini_api_fixed_prompt.ipynb
    ├── 02_test_groq_api_fixed_prompt.ipynb
    ├── 03_test_mistral_api_http_fixed_prompt.ipynb
    ├── 04_test_openrouter_free_client_fallback.ipynb
    ├── 05_test_cerebras_api_fixed_prompt.ipynb
    └── diff.txt
```

Não existe `pyproject.toml`, package metadata, `research/`, matriz Excel,
dataset-generation script, notebook de treino ou notebook de benchmark.

### `src/`

Contém o source code. [`src/config.py`](src/config.py) calcula `PROJECT_ROOT` e
os caminhos `DATASETS`, `PROMPTS` e `NOTEBOOKS`. Não há executor CLI nem módulo
de orquestração do pipeline.

### `src/core/`

- [`config.py`](src/core/config.py): `load_yaml_config`,
  `validate_pipeline_config`, `load_pipeline_config` e as nove secções
  obrigatórias.
- [`constants.py`](src/core/constants.py): versões/defaults e enums D/C/O.
- [`interfaces.py`](src/core/interfaces.py): contratos abstratos para as nove
  roles da geração e para providers de texto.
- [`schema.py`](src/core/schema.py): dataclasses que constituem um
  `CanonicalExample` e conversão para contentores serializáveis.
- [`factory.py`](src/core/factory.py): cria apenas `ManualProvider` para as
  secções configuradas.

### `src/providers/`

- [`manual_provider.py`](src/providers/manual_provider.py): fluxo interativo de
  mostrar/guardar prompt e receber uma resposta manual.
- [`gemini_provider.py`](src/providers/gemini_provider.py): integração com
  `google-genai`.
- `GroqProvider`, `MistralProvider`, `OpenRouterProvider` e
  `CerebrasProvider`: classes planeadas que ainda não existem no source code.

### `configs/`

[`configs/pipeline.manual.yaml`](configs/pipeline.manual.yaml) associa as nove
roles a `provider: manual`. [`configs/README.md`](configs/README.md) explica que
a configuração separa a escolha do provider do código. Ambos são versionados.

### `tests/`

Contém testes pytest da configuração, factory e Gemini. A cobertura atual não
inclui schema, enums, `ManualProvider`, filesystem isolado, validação de datasets
ou APIs reais. Os detalhes estão na [secção 12](#12-suite-de-testes).

### `notebooks/`

Os cinco notebooks atuais são exclusivamente smoke tests de providers. Correm
em Google Colab, leem secrets, geram dois exemplos N1, validam JSON, verificam a
presença literal da resposta no contexto e descarregam um JSON. Não são
notebooks de preparação de dataset, fine-tuning ou benchmark. O ficheiro
[`notebooks/diff.txt`](notebooks/diff.txt) é um snapshot textual auxiliar de um
diff e não é um notebook executável nem evidência experimental adicional.

### `datasets/`, `prompts/`, `experiments/`, `reports/` e `research/`

- `datasets/`: não contém artefactos mantidos no repositório;
  `datasets/generated/` e `datasets/hf/` estão ignorados por
  [`.gitignore`](.gitignore).
- `prompts/`: não contém artefactos mantidos no repositório. As prompts
  existentes estão embebidas nos notebooks, não em `.md` ou templates próprios.
- `experiments/`: caminho previsto na arquitetura e ignorado por Git; não há
  configurações ou outputs experimentais mantidos no repositório.
- `reports/`: caminho previsto na arquitetura e ignorado por Git; não há
  relatórios de resultados mantidos no repositório.
- `research/`: não existe.

Diretórios vazios e outputs ignorados não fazem parte da estrutura reproduzida
por um clone do projeto.

## 8. Classes e interfaces principais

### 8.1 Interfaces abstratas

Todas as classes desta tabela estão em
[`src/core/interfaces.py`](src/core/interfaces.py), herdam de `ABC` e não têm
construtor próprio. Definem contratos; não executam trabalho por si mesmas.

| Classe | Método público e retorno | Responsabilidade | Dependências e limitações |
|---|---|---|---|
| `DocumentLoader` | `load(source: str) -> Sequence[str]` | Carregar documentos de uma origem | Não existe implementação concreta |
| `ContextBuilder` | `build(documents) -> Sequence[Context]` | Converter textos em contextos | Depende de `Context`; sem implementação |
| `TaskGenerator` | `generate(context) -> Sequence[Task]` | Gerar tarefas para um contexto | Depende de `Context` e `Task`; sem implementação |
| `DecisionGenerator` | `decide(context, task) -> DecisionType` | Escolher D1, D2 ou D3 | Sem implementação ou regras automáticas |
| `OperationClassifier` | `classify(context, task) -> Sequence[OperationGroup]` | Identificar operações necessárias | Só os grupos O1–O7 existem no enum |
| `ComplexityClassifier` | `classify(context, task, operations) -> ComplexityLevel` | Atribuir C1–C5 | Sem implementação ou critérios executáveis |
| `GroundTruthGenerator` | `generate(context, task, expected_behaviour) -> tuple[ExpectedOutput, GroundTruth]` | Produzir output e evidência de referência | Sem implementação concreta |
| `Validator` | `validate(example) -> bool` | Aceitar ou rejeitar exemplo canónico | Não existe validator concreto |
| `Exporter` | `export(examples, options=None) -> Any` | Converter exemplos para um formato de destino | Tipo de retorno depende de futura implementação |
| `AIProvider` | `generate(prompt, response=None) -> str` | Uniformizar geração textual manual ou por API | Não define retry, structured output ou token limits |

As primeiras nove interfaces modelam roles do pipeline descrito em
[`docs/dataset/06_dataset_generation_framework.md`](docs/dataset/06_dataset_generation_framework.md).
`AIProvider` é uma abstração transversal mais simples e é a base dos providers
atualmente concretos.

### 8.2 Enums e constantes

Em [`src/core/constants.py`](src/core/constants.py):

- `DecisionType(str, Enum)`: `D1_CONTEXT_SUFFICIENT`,
  `D2_CONTEXT_INSUFFICIENT`, `D3_TASK_INCOMPATIBLE`;
- `ComplexityLevel(str, Enum)`: `C1` a `C5`;
- `OperationGroup(str, Enum)`: `O1_LOCALIZE` a
  `O7_EXECUTE_CONTEXT_INSTRUCTIONS`;
- `DEFAULT_SCHEMA_VERSION = "1.0"` e `DEFAULT_CONTEXT_TYPE = "text"`.

Por herdarem de `str`, os enums são fáceis de serializar e comparar com os
códigos documentais. Não codificam descrições, suboperações ou regras de
classificação.

### 8.3 Dataclasses do schema canónico

Todas estão em [`src/core/schema.py`](src/core/schema.py), usam apenas a standard
library e expõem `to_dict() -> dict[str, Any]`. O helper privado
`_to_plain_value()` converte enums, `datetime`, listas, tuplos e dicionários em
valores serializáveis.

| Classe | Argumentos/campos principais | Responsabilidade e relação |
|---|---|---|
| `Metadata` | `id`; `version`, `domain`, `language`, `source`, `operations`, `complexity`, `conversation_length`, `created_at`, `extra` | Identificação, proveniência e classificação do exemplo |
| `Context` | `content`; `context_type="text"`, `metadata` | Informação disponível ao modelo |
| `Task` | `instruction`; `restrictions`, `metadata` | Instrução e restrições a cumprir |
| `ExpectedBehaviour` | `decision`; `operations`, `rationale` | Decisão e operações corretas esperadas |
| `ExpectedOutput` | `content`; `output_type`, `metadata` | Resposta, pedido de contexto ou recusa esperada |
| `GroundTruth` | `supporting_facts`, `evidence`, `missing_information`, `decision_justification`, `notes`, `extra` | Evidência para validação e avaliação; não se destina diretamente ao treino |
| `CanonicalExample` | `metadata`, `context`, `task`, `expected_behaviour`, `expected_output`, `ground_truth` | Agregado completo e formato interno de referência |

Os campos sem default são obrigatórios no construtor; os restantes têm defaults
ou `default_factory`. Não existe validação de conteúdo, JSON Schema, persistência
em `.jsonl` ou version migration. O código atual usa `decision` e `operations`;
nomes sugeridos mais antigos na documentação não substituem o schema real.

### 8.4 Providers concretos

#### `ManualProvider`

- **Path:** [`src/providers/manual_provider.py`](src/providers/manual_provider.py)
- **Herança:** `AIProvider`.
- **Construtor:** `ManualProvider(prompt_path: str | Path | None = None)`.
- **Método público:** `generate(prompt: str, response: str | None = None) -> str`.
- **Funcionamento:** mostra o prompt, guarda-o em UTF-8 se `prompt_path` existir,
  devolve `response` quando fornecida ou lê linhas de `stdin` até EOF.
- **Dependências:** `pathlib` e input/output da consola.
- **Uso atual:** é o único provider reconhecido pela factory.
- **Limitações:** é interativo, não valida a resposta e não tem testes próprios;
  mesmo com `response`, mostra e pode guardar o prompt antes de devolver.

#### `GeminiProvider`

- **Path:** [`src/providers/gemini_provider.py`](src/providers/gemini_provider.py).
- **Herança:** `AIProvider`.
- **Construtor:** `GeminiProvider(model: str = "gemini-3.1-flash-lite")`.
- **Método público:** `generate(prompt: str, response: str | None = None) -> str`.
- **Funcionamento:** exige `GEMINI_API_KEY`, cria `genai.Client`, devolve uma
  resposta fornecida sem chamada de geração ou chama
  `client.models.generate_content(model=..., contents=...)`.
- **Retorno:** texto gerado; `None` vindo do SDK é normalizado para `""`.
- **Dependências:** package `google-genai`, ambiente e API Gemini.
- **Limitações:** não configura temperature, structured output, retry, timeout ou
  rate-limit handling; não está registado na factory.

### 8.5 Factory e configuração

Não existem classes de configuração. Em [`src/core/config.py`](src/core/config.py),
`load_yaml_config()` lê YAML, `validate_pipeline_config()` verifica as nove
secções e `load_pipeline_config()` combina ambas. O YAML vazio produz `{}`; uma
raiz não-mapping ou secções em falta geram `ValueError`.

A factory não é uma classe. As funções em
[`src/core/factory.py`](src/core/factory.py) são:

- `create_component(section_name, section_config) -> ManualProvider`: aceita
  apenas `provider: manual`; provider ausente ou desconhecido gera `ValueError`;
- `create_pipeline_components(config) -> dict[str, ManualProvider]`: valida o
  config e cria um componente por secção obrigatória.

### Classes planeadas

`GroqProvider`, `MistralProvider`, `OpenRouterProvider` e `CerebrasProvider` não
existem ainda como classes no source code. Um provider xAI ou Grok também não
existe. Qualquer construtor, método ou política comum além de
`AIProvider.generate()` é **Por confirmar**.

Também não existem implementações concretas de validators, dataset builders,
exporters ou das restantes interfaces do pipeline.

## 9. Packages e dependências

Não existe `pyproject.toml`; versão mínima de Python e dependências de
desenvolvimento não estão formalmente declaradas.

### Dependências do runtime atual

| Dependência | Declaração | Papel |
|---|---|---|
| `PyYAML` | [`requirements.txt`](requirements.txt) | `yaml.safe_load()` em `src/core/config.py` |
| `google-genai` | [`requirements.txt`](requirements.txt) | Cliente oficial usado por `GeminiProvider` e notebook Gemini |

### Dependências apenas observadas nos notebooks

| Dependência | Notebooks | Papel |
|---|---|---|
| `groq` | `02_test_groq_api_fixed_prompt.ipynb` instala `-U groq` | SDK da Groq |
| `requests` | Mistral, OpenRouter e Cerebras | Chamadas HTTP a endpoints compatíveis com chat completions; não é instalado explicitamente pelos notebooks |
| `google.colab` | todos | Leitura de Secrets e download de ficheiros no ambiente Colab |
| `google-genai` | Gemini | SDK Gemini; instalado numa célula |

`json`, `re`, `time` e `pathlib` pertencem à standard library. A versão das
dependências instaladas pelas células não é fixada.

### Desenvolvimento, testes e treino

- `pytest` é necessário para a suite, mas não aparece em `requirements.txt`; o
  ambiente auditado usa pytest `7.4.0`.
- Não estão declarados `openpyxl`, `datasets`, `transformers`, `trl`, `peft`,
  `unsloth`, `pandas` ou `python-dotenv`.
- Não há dependências de treino porque ainda não existem scripts/notebooks de
  treino neste repositório.

## 10. Artefactos e formatos de dados

### 10.1 Formatos realmente presentes

| Formato | Artefactos | Produção e consumo |
|---|---|---|
| `.md` | `README.md`, [`docs/`](docs/), [`configs/README.md`](configs/README.md) | Documentação humana; não há prompts `.md` |
| `.yaml` | [`configs/pipeline.manual.yaml`](configs/pipeline.manual.yaml) | Configuração lida por `load_pipeline_config()` e consumida pela factory |
| `.ipynb` | cinco ficheiros em [`notebooks/`](notebooks/) | Smoke tests Colab de APIs; incluem código, outputs e prompts |
| `.py` | [`src/`](src/) e [`tests/`](tests/) | Implementação e testes |

Não existem `.xlsx`, `.xls`, `.json`, `.jsonl`, `.csv`, `.parquet` ou artefactos
de modelo no repositório. `.csv`, `.jsonl`, `.parquet`, `.bin`, `.safetensors`,
`experiments/`, `reports/`, `checkpoints/` e `models/` são ignorados por Git.

### 10.2 Schema canónico implementado

Uma representação abreviada, baseada em [`src/core/schema.py`](src/core/schema.py),
é:

```json
{
  "metadata": {"id": "...", "version": "1.0", "operations": ["O1"]},
  "context": {"content": "...", "context_type": "text"},
  "task": {"instruction": "...", "restrictions": {}},
  "expected_behaviour": {"decision": "D1", "operations": ["O1"]},
  "expected_output": {"content": "...", "output_type": "..."},
  "ground_truth": {"supporting_facts": ["..."], "evidence": ["..."]}
}
```

É um modelo Python; não há ficheiro canónico serializado nem builder que o
escreva em JSONL.

### 10.3 Raw output dos providers

O teste Gemini guarda diretamente um array de exemplos. Os outros notebooks
guardam um objeto com metadados e `examples`:

```json
{
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "number_of_examples": 2,
  "generation_settings": {"temperature": 0.8, "domain": "Bibliotecas"},
  "examples": [
    {"context": "...", "question": "...", "answer": "..."}
  ]
}
```

OpenRouter e Cerebras acrescentam `usage`; OpenRouter acrescenta dados de
fallback e modelos pedido/real. Estes JSON são produzidos em `/content/...` e
descarregados, mas não estão guardados no projeto.

### 10.4 Formatos alvo, ainda ausentes

- **Capability matrix `.xlsx`:** **Por confirmar**; não há matriz, colunas nem
  validator implementado.
- **Canonical `.jsonl`:** deverá transportar o schema canónico, mas não existe.
- **Unsloth `.jsonl`:** formato de treino alvo mencionado na visão solicitada,
  mas não especificado nem produzido.
- **Benchmark `.jsonl`:** deverá ser independente do treino; schema específico
  **Por confirmar**.
- **Evaluation `.csv` e experiment-summary `.json`:** não existem; colunas e
  métricas **Por confirmar**.
- **Manual-review format:** não existe; campos de review **Por confirmar**.

Raw provider output, formato canónico, formato de treino, benchmark e revisão
manual não devem ser tratados como equivalentes: servem fases e níveis de
validação diferentes.

## 11. Validação de providers

As informações seguintes são extraídas exclusivamente dos cinco notebooks não
versionados e dos respetivos outputs guardados:

| Provider | Variável | SDK/método | Modelo validado | Structured output | Retry/fallback | Free tier | Estado e notebook |
|---|---|---|---|---|---|---|---|
| Google AI Studio / Gemini | `GEMINI_API_KEY` | `google-genai` | `gemini-3.1-flash-lite` | `response_mime_type="application/json"` | Sem retry/fallback explícito | **Por confirmar** | Execução bem-sucedida — [`01_test_gemini_api_fixed_prompt.ipynb`](notebooks/01_test_gemini_api_fixed_prompt.ipynb) |
| Groq | `GROQ_API_KEY` | SDK `groq` | `llama-3.3-70b-versatile` | `response_format={"type": "json_object"}` | Seleção de candidato disponível; sem retry de chamada | **Por confirmar** | Execução bem-sucedida — [`02_test_groq_api_fixed_prompt.ipynb`](notebooks/02_test_groq_api_fixed_prompt.ipynb) |
| Mistral | `MISTRAL_API_KEY` | HTTP com `requests` | `mistral-small-latest` | `response_format={"type": "json_object"}` | Sem retry/fallback | **Por confirmar** | Execução bem-sucedida — [`03_test_mistral_api_http_fixed_prompt.ipynb`](notebooks/03_test_mistral_api_http_fixed_prompt.ipynb) |
| OpenRouter Free | `OPENROUTER_API_KEY` | HTTP com `requests` | `google/gemma-4-26b-a4b-it:free` após Qwen 429 | `response_format={"type": "json_object"}` | 2 tentativas/modelo; `Retry-After`; fallback sequencial | Modelos com suffix `:free` | Execução bem-sucedida — [`04_test_openrouter_free_client_fallback.ipynb`](notebooks/04_test_openrouter_free_client_fallback.ipynb) |
| Cerebras | `CEREBRAS_API_KEY` | HTTP com `requests` | `gemma-4-31b` | `response_format={"type": "json_object"}` | Até 3 tentativas para HTTP 408/409/429/5xx; sem fallback após seleção | **Por confirmar** | Células bem-sucedidas, nota final “em validação” — [`05_test_cerebras_api_fixed_prompt.ipynb`](notebooks/05_test_cerebras_api_fixed_prompt.ipynb) |

O protocolo equivalente usa dois exemplos N1 com `temperature=0.8` e, exceto no
Gemini, `max_tokens=4000`. Cada notebook:

1. autentica e confirma uma resposta mínima “Olá”;
2. gera exatamente dois exemplos;
3. remove opcionalmente fences Markdown;
4. faz parse JSON;
5. valida a coleção e os campos `context`, `question`, `answer`;
6. verifica o número exato de exemplos;
7. normaliza strings e verifica que `answer` aparece em `context`;
8. apresenta, guarda e descarrega o resultado.

Groq, Mistral, OpenRouter e Cerebras guardam provider/model e generation
settings. OpenRouter e Cerebras guardam `usage` quando devolvido pela API.
Gemini guarda apenas a lista de exemplos nesta versão. A presença literal da
resposta é uma verificação estrutural útil, mas não prova por si só unicidade,
qualidade linguística ou correção cognitiva completa.

Validar providers separadamente reduz incerteza antes de implementar a abstração
comum: confirma autenticação, disponibilidade de modelos, formato JSON,
rate limits e diferenças de API. Essa validação real complementa, mas não
substitui, testes unitários com mocks.

## 12. Suite de testes

### 12.1 Cobertura atual

| Test file | Target | O que valida | Usa mocks? |
|---|---|---|---|
| [`tests/test_config.py`](tests/test_config.py) | `src/core/config.py` e `configs/pipeline.manual.yaml` | O caso normal: todas as nove secções obrigatórias existem no YAML carregado | Não |
| [`tests/test_factory.py`](tests/test_factory.py) | `src/core/factory.py` | Criação de um `ManualProvider` por secção e `ValueError` claro para provider desconhecido | Não |
| [`tests/test_gemini_provider.py`](tests/test_gemini_provider.py) | `src/providers/gemini_provider.py` | Interface, API key, modelo default, prompt, retorno da API, short-circuit, chave ausente e texto `None` | Sim |

`test_config.py` lê um ficheiro real do repositório, por isso exerce um cenário
de filesystem simples, mas não usa diretório temporário. Não há fixtures pytest
personalizadas. Não existem testes para:

- YAML vazio, raiz não-mapping ou secções em falta;
- provider ausente na factory;
- leitura/escrita e consola do `ManualProvider`;
- dataclasses, serialização, enums ou interfaces abstratas;
- timeouts, authentication errors, rate limits ou malformed Gemini responses;
- validators, datasets, splits, exporters ou benchmarks;
- APIs reais.

### 12.2 Comandos e resultado factual

O comando verificado deve ser executado na raiz do repositório:

```bash
python -m pytest -q
```

Resultado da verificação mais recente:

```text
7 passed in 1.19s
```

Isto corresponde a 7 testes aprovados, 0 failed, 0 skipped e 0 warnings
reportados. O tempo pode variar entre execuções. A forma `python -m pytest`
garante que a raiz do projeto participa na resolução dos imports de `src`.

### 12.3 Interpretar resultados pytest

- **Passing test:** o comportamento observado correspondeu às assertions para
  aquele cenário; não prova propriedades que o teste não cobre.
- **Failing assertion:** o módulo foi importado e executado, mas o valor ou a
  interação observada divergiu do esperado.
- **Fixture failure:** a preparação partilhada falhou antes ou depois do corpo do
  teste. Não existem fixtures personalizadas atualmente.
- **Import error:** pytest não conseguiu importar o teste ou produção; nenhum
  comportamento desse módulo foi validado.
- **Network-related failure:** seria esperada em integração real por timeout,
  DNS, rate limit ou autenticação. Os unit tests Gemini não usam rede, portanto
  uma falha de rede nesses testes indicaria que o isolamento deixou de funcionar.

## 13. O que são mocks

Um **mock** substitui uma dependência externa durante um unit test e regista como
foi utilizado. Chamadas reais de API normalmente não pertencem à suite unitária:
dependem de rede, credenciais, quotas, disponibilidade e respostas não totalmente
determinísticas. Um mock torna o teste rápido, determinístico e gratuito.

```text
Unit test com mock:

GeminiProvider
      ↓
Mock de genai.Client
      ↓
Resposta predeterminada

Validação de integração real:

GeminiProvider / notebook
      ↓
API externa
      ↓
Resposta real do provider
```

Mocks permitem simular sucesso, resposta malformada, timeout, erro de
autenticação e rate limit sem provocar esses eventos externamente. Contudo, um
mock não prova que a credencial é válida, que o endpoint não mudou ou que o
modelo está disponível hoje. Os notebooks atuais exercem APIs reais
separadamente.

Termos relacionados:

- **mock:** objeto controlado que devolve valores e permite confirmar chamadas,
  argumentos e contagem de invocações;
- **stub:** substituição simples que fornece respostas predefinidas, sem exigir
  verificação detalhada das interações;
- **fixture:** preparação reutilizável de estado para testes; pytest suporta
  fixtures, mas este projeto ainda não define fixtures próprias;
- **monkeypatch:** alteração temporária de atributos, environment variables ou
  funções durante um teste; `unittest.mock.patch` cumpre esse papel nos testes
  atuais, embora a fixture `monkeypatch` de pytest não seja usada;
- **integration test:** combina o código real com uma dependência real, como a
  API Gemini;
- **end-to-end test:** percorre o fluxo completo, por exemplo matriz → geração →
  validação → dataset → treino → benchmark. Não existe atualmente.

## 14. Como funcionam os mocks existentes

[`tests/test_gemini_provider.py`](tests/test_gemini_provider.py) aplica:

```python
@patch("src.providers.gemini_provider.genai.Client")
```

Este path é importante: substitui o símbolo `Client` no local onde
`GeminiProvider` o procura, não faz patch genérico de toda a package. O mock do
cliente expõe automaticamente `models.generate_content`; o teste define:

```python
mock_client.return_value.models.generate_content.return_value.text = (
    "Generated response"
)
```

As assertions confirmam:

- `GeminiProvider` é uma instância de `AIProvider`;
- o cliente recebe `api_key="test-key"`;
- `generate_content` recebe o modelo default e `contents="Test prompt"`;
- o retorno é exatamente `"Generated response"`;
- uma `response="Provided response"` evita `generate_content`;
- sem `GEMINI_API_KEY`, é lançado `ValueError` e o cliente não é criado;
- `response.text = None` produz `""`, mantendo o return type `str`.

As environment variables são simuladas com
`patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})`. No teste de chave
ausente, `clear=True` cria temporariamente um environment vazio. Não há secrets
reais no teste.

O objeto de resposta vazio também é um `Mock`. Não são simulados timeout,
authentication error, rate limit, exceção do SDK ou JSON malformado. Não são
isoladas operações de filesystem porque estes testes não escrevem ficheiros.

## 15. Como passar de mocks para testes reais

Os mocks **não devem ser removidos** dos unit tests. A estratégia proposta é:

1. manter unit tests rápidos e isolados;
2. acrescentar integration tests opcionais;
3. registá-los com um marker pytest, por exemplo `integration`;
4. fazer skip automático quando a API key não existe;
5. executá-los explicitamente quando for necessário validar a API;
6. usar uma prompt mínima e um limite baixo de tokens;
7. nunca gerar datasets grandes na suite normal.

Estrutura **planeada**, não existente:

```text
tests/
├── unit/
│   └── mocked provider tests
└── integration/
    └── real API smoke tests
```

Um smoke test planeado deverá ler a variável, chamar o provider com uma prompt
mínima, fazer skip se a chave faltar e verificar apenas que recebe uma string não
vazia. Não deverá exigir texto exato, porque a geração pode variar. Deverá
registar provider/model e respeitar quota, rate limits e custos.

Após adicionar e configurar o marker, os comandos propostos seriam:

```bash
pytest
pytest -m "not integration"
pytest -m integration
```

Estes comandos de markers **ainda não são operacionais como workflow suportado**:
não há marker configurado nem integration tests. Enquanto o import path não for
configurado, deverá também ser usada a forma `python -m pytest ...` neste
ambiente. Os notebooks em [`notebooks/`](notebooks/) são hoje a validação real
disponível.

## 16. Variáveis de ambiente e secrets

| Variável | Estado | Consumidor atual |
|---|---|---|
| `GEMINI_API_KEY` | Implementada no `GeminiProvider` e validada em notebook | `src/providers/gemini_provider.py`, notebook 01 |
| `GROQ_API_KEY` | Validada apenas em notebook | notebook 02 |
| `MISTRAL_API_KEY` | Validada apenas em notebook | notebook 03 |
| `OPENROUTER_API_KEY` | Validada apenas em notebook | notebook 04 |
| `CEREBRAS_API_KEY` | Usada em execução Cerebras; estado formal do notebook contraditório | notebook 05 |

Não existe `.env.example`. O ficheiro [`.gitignore`](.gitignore) exclui `.env`,
`.venv/`, checkpoints, modelos e formatos de dados grandes. Regras de segurança:

- nunca guardar API keys no código, notebooks, outputs ou Git;
- em desenvolvimento local, um `.env` pode guardar valores, mas o projeto não
  inclui `python-dotenv` nem faz loading automático; é necessário exportar as
  variáveis ou usar tooling externo;
- em Colab, usar **Secrets** e ativar o acesso do notebook;
- em CI, usar secrets protegidos do serviço;
- um futuro `.env.example` deverá conter apenas nomes e valores vazios.

## 17. Executar o projeto

Todos os comandos locais partem da raiz `grounded-behavior-framework/`.

### 17.1 Ambiente local

O projeto não fixa a versão de Python. O ambiente auditado usa Python `3.11.7`.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Input: [`requirements.txt`](requirements.txt). Output: ambiente virtual com
`PyYAML` e `google-genai`. Erros comuns incluem Python/venv ausente, acesso ao
package index bloqueado e versão incompatível de uma dependência. `pytest` não é
instalado por este ficheiro e terá de existir no ambiente de desenvolvimento.

### 17.2 Testes

```bash
python -m pytest -q
```

Este é o comando funcional confirmado. O input é `tests/`; o output esperado no
estado auditado é `7 passed`. `pytest -q` isoladamente falha atualmente com
`ModuleNotFoundError: src`, conforme documentado na secção 12.

Podem executar-se módulos específicos:

```bash
python -m pytest -q tests/test_config.py
python -m pytest -q tests/test_factory.py
python -m pytest -q tests/test_gemini_provider.py
```

### 17.3 Provider manual

Não existe CLI. `ManualProvider` só pode ser usado através de código Python que
o importe e chame `generate()`. A configuração YAML pode ser carregada e a
factory pode construir componentes, mas não há executor que percorra o pipeline.

### 17.4 Notebooks

Abrir individualmente os ficheiros de [`notebooks/`](notebooks/) no Google
Colab, configurar o Secret indicado e executar as células por ordem. Input:
secret e prompt embebida. Output: JSON em `/content/<provider>_outputs/`, seguido
de download local.

Erros comuns: Secret ausente, modelo removido, HTTP 401/403, HTTP 429, timeout,
structured output não suportado ou JSON inválido. Apenas OpenRouter e Cerebras
têm retry explícito; apenas OpenRouter tenta vários modelos após falha.

Não existem comandos para validar uma matriz, gerar prompts em batch, unir
outputs, construir datasets, treinar ou avaliar. Essas capacidades são
planeadas.

## 18. Fluxo de geração do dataset

Este é o workflow alvo solicitado. A coluna Estado evita confundir desenho com
implementação:

| Passo | Atividade | Estado atual |
|---:|---|---|
| 1 | Definir ou atualizar a coverage matrix | **Planeado**; matriz ausente |
| 2 | Validar dimensões, valores e cobertura | **Planeado**; validator ausente |
| 3 | Gerar prompts rastreáveis | **Parcial/manual**; há apenas prompts fixas embebidas nos notebooks |
| 4 | Enviar prompts a providers validados | **Notebook-based** para cinco smoke tests; `GeminiProvider` está implementado, mas ainda não está na factory |
| 5 | Guardar raw outputs | **Notebook-based fora do repositório** em `/content`; outputs finais ausentes |
| 6 | Validar a estrutura JSON | **Notebook-based** para dois exemplos; validator comum planeado |
| 7 | Anexar metadados de rastreabilidade | **Parcial**; varia por notebook |
| 8 | Rejeitar exemplos inválidos | **Parcial**; notebooks lançam exceções, sem workflow de review/rejeição |
| 9 | Unir exemplos aprovados | **Planeado** |
| 10 | Criar `train`/`validation`/`test`/`benchmark` | **Planeado** |
| 11 | Exportar para Unsloth | **Planeado** |
| 12 | Fazer fine-tuning | **Planeado** |
| 13 | Avaliar antes e depois | **Planeado** |
| 14 | Analisar por capacidade/subskill | **Planeado** |
| 15 | Atualizar currículo e cobertura | **Planeado** |

O workflow deve preservar o raw output antes de limpeza, separar validação
estrutural de validação cognitiva, impedir que benchmark entre no treino e
manter ligações entre exemplo, prompt, provider, dataset e experiência.

## 19. Rastreabilidade

### Campos atuais

O schema implementado já permite:

- `Metadata.id`, `version`, `domain`, `language`, `source`;
- `operations`, `complexity`, `conversation_length`, `created_at`;
- `extra` em vários blocos para extensões ainda não formalizadas;
- `Context.metadata`, `Task.metadata` e `ExpectedOutput.metadata`;
- decisão, rationale, supporting facts, evidence, missing information, notes.

Os raw JSON de alguns notebooks registam `provider`, `model`,
`number_of_examples`, `generation_settings` e `examples`. OpenRouter e Cerebras
incluem `usage`; OpenRouter distingue candidate, requested e actual model.

### Campos a formalizar

Uma política futura de rastreabilidade poderá necessitar de example ID, batch ID,
curriculum level, capability, subskill, domain, document style, fact/entity type,
context length, fact position, distractor/question type, generator provider e
model, prompt version, validator, dataset version/split, experiment ID, review
status, generation date, token usage e resultado before/after. Estes nomes são
requisitos alvo; **não existe ainda schema acordado para todos eles**.

Esta rastreabilidade permitirá filtrar resultados por modelo, capacidade,
domínio e origem, medir melhorias/regressões e reconstruir a linhagem de cada
exemplo. Campos devem ser promovidos de `extra` para o schema apenas através de
uma alteração versionada e documentada.

## 20. Outputs finais

### Outputs científicos

**Atuais:** visão do projeto, modelo D1–D3, taxonomia O1–O7 com suboperações,
escala C1–C5, especificação conceptual do dataset e arquitetura modular em
[`docs/`](docs/).

**Alvo:** taxonomia de capacidades/subskills, currículo progressivo, matriz de
cobertura, metodologia reproduzível, evidência before/after, análise por
capacidade e regressão e artigos/relatórios. Não há resultados quantitativos ou
artigos no repositório.

### Outputs de dataset

**Atuais:** nenhum dataset é mantido no repositório. Existem apenas exemplos
embebidos nos outputs dos notebooks.

**Alvo:** dataset canónico, splits train/validation/test, benchmark externo,
formato Unsloth, ficheiros de revisão manual e metadados completos de
rastreabilidade.

### Outputs de modelo

**Atuais:** nenhum.

**Alvo:** LoRA adapters, checkpoints, configuração de inference e resultados de
avaliação. Formato, naming e destino de publicação são **Por confirmar**.

### Outputs de software

**Atuais:** interfaces, schema, enums, configuração, provider manual, factory
manual, `GeminiProvider`, testes unitários e notebooks de validação.

**Alvo:** providers restantes, matrix validator, prompt generator, common output
validator, dataset builder, exporters e notebooks/pipelines de treino e
avaliação.

## 21. Limitações

- A investigação dependerá de dados sintéticos, sujeitos a erros e generator
  style bias.
- O protocolo atual testa só dois exemplos por provider, no mesmo domínio e com
  a mesma configuração cognitiva; não mede generalização.
- Verificar `answer in context` não prova que a resposta é única, completa ou
  cognitivamente adequada; é necessária amostragem/revisão humana.
- Os providers podem alterar free tiers, modelos, rate limits e formatos; os
  resultados dos notebooks são snapshots, não garantias atuais.
- Geração por API não é perfeitamente determinística, sobretudo com
  `temperature=0.8`.
- Não há seeds, versões fixas de packages, timestamps experimentais ou raw JSON
  versionado.
- A capacidade de modelos pequenos pode impor limites mesmo com currículo bem
  estruturado.
- Fine-tuning pode causar overfitting e regressões; ainda não existem medições
  neste repositório.
- Um benchmark externo só é válido se permanecer independente do treino e da
  seleção iterativa de exemplos.
- O roadmap versionado em
  [`docs/dataset/07_project_roadmap.md`](docs/dataset/07_project_roadmap.md) ainda
  marca a fase Core como não iniciada, embora parte do core já exista; necessita
  atualização futura fora desta tarefa.
- A factory só suporta manual, não há pipeline runner e os providers API comuns
  estão incompletos.
- Os raw JSON descarregados pelos notebooks não são preservados no repositório,
  o que limita a auditoria posterior das respostas completas das APIs.

## 22. Roadmap

Estado baseado nos componentes mantidos no repositório, não apenas no roadmap
documental:

1. [x] Definir visão grounded, decisões, operações, complexidade, schema e
   interfaces.
2. [x] Implementar configuração e `ManualProvider`.
3. [x] Implementar a factory manual e os respetivos testes.
4. [x] Implementar `GeminiProvider` e unit tests com mocks.
5. [x] Registar os cinco notebooks de validação de providers.
6. [ ] Declarar dependências de desenvolvimento e configuração pytest.
7. [ ] Registar `GeminiProvider` na factory quando a seleção de providers API
   fizer parte da arquitetura operacional.
8. [ ] Implementar Groq, Mistral, OpenRouter e Cerebras sob `AIProvider`, com
   unit tests mockados.
9. [ ] Adicionar integration smoke tests opcionais.
10. [ ] Definir N1/subskills e integrar uma coverage matrix.
11. [ ] Implementar prompt generation, validação comum e merge de outputs.
12. [ ] Construir dataset multi-provider e splits independentes.
13. [ ] Exportar para o formato de treino selecionado e executar fine-tuning com
    configuração registada.
14. [ ] Executar benchmarks internos/externos e analisar aquisição e regressão
    por capacidade.
15. [ ] Decidir, com evidência, se o currículo deve avançar para o nível
    cognitivo seguinte.

## 23. Checklist de reprodutibilidade

Antes de considerar uma geração ou experiência reproduzível, registar:

- [ ] versão de Python;
- [ ] lock ou versões exatas das dependências;
- [ ] random seeds aplicáveis;
- [ ] dataset ID e versão;
- [ ] matrix ID e versão;
- [ ] prompt ID, versão e conteúdo;
- [ ] provider, endpoint e modelo pedido/real;
- [ ] generation parameters (`temperature`, `max_tokens`, structured output);
- [ ] training parameters, base model e hardware;
- [ ] benchmark ID e versão;
- [ ] raw outputs imutáveis;
- [ ] outputs validados e motivos de rejeição;
- [ ] ficheiros de resultados e métricas;
- [ ] Git revision e estado do repositório no momento da execução;
- [ ] data/hora e ambiente de execução;
- [ ] token usage, quota/custo quando disponíveis;
- [ ] separação comprovada entre treino e benchmark.

Atualmente, esta checklist não está integralmente satisfeita pelos notebooks.

## 24. Regras de contribuição e segurança

- Nunca fazer commit de API keys, `.env`, tokens ou Secrets do Colab.
- Nunca usar exemplos do benchmark para treino, seleção de prompts ou geração do
  dataset de treino.
- Não alterar silenciosamente o schema canónico; versionar e documentar qualquer
  migração.
- Não misturar raw, generated, reviewed e validated examples sem um status
  explícito.
- Não sobrescrever outputs experimentais; usar IDs/versões e preservar raw data.
- Manter provider, requested model, actual model, prompt e settings em cada
  geração.
- Adicionar unit tests com mocks para cada provider novo.
- Adicionar testes reais apenas como integration tests opcionais e económicos.
- Rever amostras humanas e guardar critérios de aceitação/rejeição.
- Preservar o benchmark externo como avaliação independente.
- Não apresentar outputs locais ou ignorados como resultados preservados no
  repositório.
- Notebooks devem orquestrar código; lógica reutilizável deve migrar para
  `src/`, conforme
  [`docs/architecture/02_project_architecture.md`](docs/architecture/02_project_architecture.md).

## 25. Guia de navegação

Onde encontrar:

- **visão e objetivo científico:**
  [`docs/architecture/01_project_vision.md`](docs/architecture/01_project_vision.md);
- **arquitetura e política de artefactos:**
  [`docs/architecture/02_project_architecture.md`](docs/architecture/02_project_architecture.md);
- **filosofia e especificação do dataset:**
  [`docs/dataset/01_dataset_specification.md`](docs/dataset/01_dataset_specification.md);
- **decisões D1–D3:**
  [`docs/dataset/02_context_decision_model.md`](docs/dataset/02_context_decision_model.md)
  e [`src/core/constants.py`](src/core/constants.py);
- **operações e suboperações:**
  [`docs/dataset/03_context_operations.md`](docs/dataset/03_context_operations.md);
- **complexidade C1–C5:**
  [`docs/dataset/04_complexity_model.md`](docs/dataset/04_complexity_model.md);
- **schema canónico:**
  [`docs/dataset/05_canonical_dataset_schema.md`](docs/dataset/05_canonical_dataset_schema.md)
  e [`src/core/schema.py`](src/core/schema.py);
- **framework conceptual e interfaces:**
  [`docs/dataset/06_dataset_generation_framework.md`](docs/dataset/06_dataset_generation_framework.md)
  e [`src/core/interfaces.py`](src/core/interfaces.py);
- **roadmap documental:**
  [`docs/dataset/07_project_roadmap.md`](docs/dataset/07_project_roadmap.md);
- **configuração manual:**
  [`configs/pipeline.manual.yaml`](configs/pipeline.manual.yaml);
- **factory:** [`src/core/factory.py`](src/core/factory.py);
- **providers:** [`src/providers/`](src/providers/);
- **notebooks de validação de providers:** [`notebooks/`](notebooks/);
- **testes:** [`tests/`](tests/);
- **capability definitions N1/subskills e coverage matrix:** **Por confirmar**;
- **datasets, treino, benchmarks e relatórios de resultados:** ainda não existem
  no repositório.
