"""Modelos de dados que compõem um exemplo canónico do framework."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .constants import (
    DEFAULT_CONTEXT_TYPE,
    DEFAULT_SCHEMA_VERSION,
    ComplexityLevel,
    DecisionType,
    OperationGroup,
)


def _to_plain_value(value: Any) -> Any:
    """Converte valores especiais em estruturas Python serializáveis.

    Enums são reduzidos ao respetivo valor, datas passam para ISO 8601 e
    contentores aninhados são processados recursivamente. Outros valores são
    devolvidos sem alteração.
    """

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _to_plain_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain_value(item) for item in value]
    return value


@dataclass
class Metadata:
    """Guarda os metadados técnicos de um exemplo canónico.

    Reúne identificação, proveniência, idioma, operações e complexidade. O
    output de ``to_dict`` é um dicionário simples adequado a JSON ou YAML.
    """

    id: str
    version: str = DEFAULT_SCHEMA_VERSION
    domain: str = ""
    language: str = ""
    source: str = ""
    operations: list[OperationGroup] = field(default_factory=list)
    complexity: ComplexityLevel | None = None
    conversation_length: int = 1
    created_at: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Devolve todos os metadados como valores Python serializáveis."""
        return _to_plain_value(asdict(self))


@dataclass
class Context:
    """Representa a informação disponibilizada ao modelo.

    Contém o texto, o tipo de contexto e metadados livres. ``to_dict`` produz
    a representação serializável usada na persistência do exemplo.
    """

    content: str
    context_type: str = DEFAULT_CONTEXT_TYPE
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Devolve o contexto como um dicionário serializável."""
        return _to_plain_value(asdict(self))


@dataclass
class Task:
    """Representa uma instrução a executar com o contexto fornecido.

    Além da instrução, conserva restrições e metadados específicos. O output
    de ``to_dict`` é uma estrutura simples para exportação.
    """

    instruction: str
    restrictions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Devolve a tarefa como um dicionário serializável."""
        return _to_plain_value(asdict(self))


@dataclass
class ExpectedBehaviour:
    """Descreve o comportamento esperado na resolução de um exemplo.

    Combina a decisão, as operações necessárias e uma justificação opcional.
    ``to_dict`` converte também os enums nos respetivos códigos textuais.
    """

    decision: DecisionType
    operations: list[OperationGroup] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Devolve o comportamento esperado numa forma serializável."""
        return _to_plain_value(asdict(self))


@dataclass
class ExpectedOutput:
    """Representa o output correto esperado para uma tarefa.

    Pode conter uma resposta, um pedido de contexto ou uma recusa fundamentada,
    acompanhado pelo tipo de output e metadados adicionais.
    """

    content: str
    output_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Devolve o output esperado como um dicionário serializável."""
        return _to_plain_value(asdict(self))


@dataclass
class GroundTruth:
    """Agrega os dados de referência para validação e avaliação.

    Regista factos, evidências, informação em falta, justificações e notas. O
    output de ``to_dict`` pode ser persistido juntamente com o exemplo.
    """

    supporting_facts: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    decision_justification: str = ""
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Devolve o ground truth como valores Python serializáveis."""
        return _to_plain_value(asdict(self))


@dataclass
class CanonicalExample:
    """Agrega todas as partes de um exemplo canónico completo.

    Serve como formato comum entre geração, treino e benchmarks. ``to_dict``
    devolve toda a árvore de dados pronta para serialização.
    """

    metadata: Metadata
    context: Context
    task: Task
    expected_behaviour: ExpectedBehaviour
    expected_output: ExpectedOutput
    ground_truth: GroundTruth

    def to_dict(self) -> dict[str, Any]:
        """Devolve recursivamente o exemplo completo num dicionário simples."""
        return _to_plain_value(asdict(self))
