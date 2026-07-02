# Project Vision

## 1. Motivação

Os Small Language Models (SLMs) estão a tornar-se cada vez mais
interessantes para aplicações locais, privadas e de baixo custo. No
entanto, a sua utilização continua limitada devido à reduzida capacidade
cognitiva e à tendência para produzir respostas incorretas ou
alucinações quando comparados com modelos de maior dimensão.

## 2. Problema

Atualmente, existem poucas metodologias sistemáticas para ensinar
modelos pequenos a responder exclusivamente com base em informação
fornecida pelo utilizador. Na maioria dos casos, os modelos recorrem ao
conhecimento previamente adquirido durante o treino, dificultando a
construção de assistentes virtuais fiáveis em domínios específicos.

## 3. Objetivo

Desenvolver uma framework que permita treinar e avaliar Small Language
Models para responderem exclusivamente com base no contexto fornecido,
privilegiando o comportamento do modelo em detrimento da memorização de
conhecimento.

## 4. Âmbito

O projeto inclui:

- definição de uma metodologia de construção de datasets;
- geração automática de datasets comportamentais;
- fine-tuning de Small Language Models;
- avaliação sistemática do comportamento dos modelos.

O projeto não pretende construir uma aplicação final nem desenvolver um
sistema RAG completo. Esses cenários serão utilizados apenas como casos
de estudo.

## 5. Resultados esperados

No final do projeto pretende-se disponibilizar:

- uma framework reutilizável para criação de datasets comportamentais;
- uma metodologia de avaliação de Small Language Models;
- exemplos de fine-tuning em diferentes modelos;
- documentação técnica e científica que permita reproduzir todo o processo.
