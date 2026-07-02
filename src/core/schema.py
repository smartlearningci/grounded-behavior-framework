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
    """Convert dataclass and enum values into plain Python containers."""

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
    """Technical metadata for a canonical dataset example."""

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
        return _to_plain_value(asdict(self))


@dataclass
class Context:
    """Information available to the model."""

    content: str
    context_type: str = DEFAULT_CONTEXT_TYPE
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_plain_value(asdict(self))


@dataclass
class Task:
    """Instruction to execute using only the provided context."""

    instruction: str
    restrictions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_plain_value(asdict(self))


@dataclass
class ExpectedBehaviour:
    """Expected decision and operation groups for an example."""

    decision: DecisionType
    operations: list[OperationGroup] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _to_plain_value(asdict(self))


@dataclass
class ExpectedOutput:
    """Expected answer, context request, or grounded refusal."""

    content: str
    output_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_plain_value(asdict(self))


@dataclass
class GroundTruth:
    """Reference data used for validation and evaluation."""

    supporting_facts: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    decision_justification: str = ""
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_plain_value(asdict(self))


@dataclass
class CanonicalExample:
    """Canonical example shared by generation, training, and benchmarks."""

    metadata: Metadata
    context: Context
    task: Task
    expected_behaviour: ExpectedBehaviour
    expected_output: ExpectedOutput
    ground_truth: GroundTruth

    def to_dict(self) -> dict[str, Any]:
        return _to_plain_value(asdict(self))
