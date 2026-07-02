from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .constants import (
    DEFAULT_CONTEXT_MODALITY,
    DEFAULT_SCHEMA_VERSION,
    Complexity,
    Decision,
    Operation,
)


@dataclass(frozen=True)
class Document:
    """Source document loaded before context construction."""

    content: str
    id: Optional[str] = None
    source: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Metadata:
    """Technical metadata for a canonical dataset example."""

    id: str
    domain: str
    language: str
    operations: tuple[Operation, ...]
    complexity: Complexity
    version: str = DEFAULT_SCHEMA_VERSION
    source: Optional[str] = None
    conversation_length: int = 1
    created_at: Optional[datetime] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Context:
    """Information available to the model for a task."""

    content: str
    modality: str = DEFAULT_CONTEXT_MODALITY
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Task:
    """Instruction that should be executed using only the context."""

    instruction: str
    restrictions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExpectedBehaviour:
    """Decision and operation labels expected before producing an answer."""

    decision: Decision
    operations: tuple[Operation, ...] = field(default_factory=tuple)
    rationale: Optional[str] = None


@dataclass(frozen=True)
class ExpectedOutput:
    """Expected final answer, request for context, or grounded refusal."""

    content: str
    output_type: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GroundTruth:
    """Reference information used by evaluation, not model training."""

    supporting_facts: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[str, ...] = field(default_factory=tuple)
    missing_information: tuple[str, ...] = field(default_factory=tuple)
    decision_justification: Optional[str] = None
    notes: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetExample:
    """Canonical dataset example used across generation, training, and benchmark."""

    metadata: Metadata
    context: Context
    task: Task
    expected_behaviour: ExpectedBehaviour
    expected_output: ExpectedOutput
    ground_truth: GroundTruth
