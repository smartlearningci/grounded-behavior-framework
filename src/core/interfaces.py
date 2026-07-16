"""Contratos abstratos para as etapas e providers do framework."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .constants import ComplexityLevel, DecisionType, OperationGroup
from .schema import (
    CanonicalExample,
    Context,
    ExpectedBehaviour,
    ExpectedOutput,
    GroundTruth,
    Task,
)


class DocumentLoader(ABC):
    """Contrato para obter documentos a partir de uma origem.

    O objetivo é isolar o acesso à fonte; as implementações produzem uma
    sequência de conteúdos textuais que alimenta a construção de contextos.
    """

    @abstractmethod
    def load(self, source: str) -> Sequence[str]:
        """Carrega ``source`` e devolve os textos dos documentos encontrados."""


class ContextBuilder(ABC):
    """Contrato para transformar documentos em contextos estruturados.

    As implementações recebem textos brutos e devolvem objetos ``Context``
    que podem ser usados pelas restantes etapas do pipeline.
    """

    @abstractmethod
    def build(self, documents: Sequence[str]) -> Sequence[Context]:
        """Constrói e devolve os contextos derivados de ``documents``."""


class TaskGenerator(ABC):
    """Contrato para criar tarefas adequadas a um contexto.

    O output é uma sequência de objetos ``Task`` candidatos, cada um com uma
    instrução que deverá ser resolvida com a informação do contexto recebido.
    """

    @abstractmethod
    def generate(self, context: Context) -> Sequence[Task]:
        """Gera e devolve tarefas candidatas para ``context``."""


class DecisionGenerator(ABC):
    """Contrato para avaliar se o contexto permite executar uma tarefa.

    A avaliação produz um ``DecisionType`` que indica suficiência,
    insuficiência ou incompatibilidade da tarefa.
    """

    @abstractmethod
    def decide(self, context: Context, task: Task) -> DecisionType:
        """Devolve a decisão esperada para o par ``context`` e ``task``."""


class OperationClassifier(ABC):
    """Contrato para identificar as operações necessárias numa tarefa.

    O resultado contém um ou mais ``OperationGroup`` e descreve o tipo de
    raciocínio ou transformação exigido pelo exemplo.
    """

    @abstractmethod
    def classify(self, context: Context, task: Task) -> Sequence[OperationGroup]:
        """Classifica e devolve as operações requeridas pelo par recebido."""


class ComplexityClassifier(ABC):
    """Contrato para atribuir complexidade cognitiva a um exemplo.

    Combina o contexto, a tarefa e as operações classificadas para produzir
    um único ``ComplexityLevel``.
    """

    @abstractmethod
    def classify(
        self,
        context: Context,
        task: Task,
        operations: Sequence[OperationGroup],
    ) -> ComplexityLevel:
        """Calcula e devolve o nível de complexidade dos dados recebidos."""


class GroundTruthGenerator(ABC):
    """Contrato para gerar a resposta de referência e a sua fundamentação.

    O resultado agrega um ``ExpectedOutput`` com a resposta esperada e um
    ``GroundTruth`` com evidências úteis para validação e avaliação.
    """

    @abstractmethod
    def generate(
        self,
        context: Context,
        task: Task,
        expected_behaviour: ExpectedBehaviour,
    ) -> tuple[ExpectedOutput, GroundTruth]:
        """Devolve a resposta esperada e o ground truth do exemplo."""


class Validator(ABC):
    """Contrato para verificar a validade de exemplos canónicos.

    As implementações devolvem um booleano: ``True`` para um exemplo aceite e
    ``False`` quando o exemplo viola as regras de validação.
    """

    @abstractmethod
    def validate(self, example: CanonicalExample) -> bool:
        """Valida ``example`` e devolve se este deve ser aceite."""


class Exporter(ABC):
    """Contrato para converter exemplos canónicos num formato de destino.

    O output depende da implementação e das opções fornecidas, permitindo
    exportar para ficheiros, objetos serializáveis ou integrações externas.
    """

    @abstractmethod
    def export(
        self,
        examples: Iterable[CanonicalExample],
        options: Mapping[str, Any] | None = None,
    ) -> Any:
        """Exporta ``examples`` segundo ``options`` e devolve o resultado."""


@dataclass
class GenerationRequest:
    """Reúne os parâmetros comuns de um pedido de geração de texto."""

    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    model_candidates: list[str] = field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None
    require_json: bool = False


@dataclass
class GenerationResult:
    """Devolve texto gerado e metadados comuns da comunicação com o provider."""

    text: str
    provider: str
    requested_model: str | None = None
    actual_model: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    attempts: list[dict[str, Any]] = field(default_factory=list)


class AIProvider(ABC):
    """Contrato estável para providers usados na geração do dataset."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Executa um pedido de geração e devolve texto com a sua proveniência."""
