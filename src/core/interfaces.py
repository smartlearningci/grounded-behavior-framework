from abc import ABC, abstractmethod
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
    """Load source documents."""

    @abstractmethod
    def load(self, source: str) -> Sequence[str]:
        """Return document contents loaded from a source."""


class ContextBuilder(ABC):
    """Build contexts from document contents."""

    @abstractmethod
    def build(self, documents: Sequence[str]) -> Sequence[Context]:
        """Return contexts derived from documents."""


class TaskGenerator(ABC):
    """Generate tasks for a context."""

    @abstractmethod
    def generate(self, context: Context) -> Sequence[Task]:
        """Return candidate tasks for a context."""


class DecisionGenerator(ABC):
    """Determine the expected context sufficiency decision."""

    @abstractmethod
    def decide(self, context: Context, task: Task) -> DecisionType:
        """Return the expected decision for a context and task."""


class OperationClassifier(ABC):
    """Classify the operation groups required by a task."""

    @abstractmethod
    def classify(self, context: Context, task: Task) -> Sequence[OperationGroup]:
        """Return one or more operation groups."""


class ComplexityClassifier(ABC):
    """Classify the cognitive complexity of an example."""

    @abstractmethod
    def classify(
        self,
        context: Context,
        task: Task,
        operations: Sequence[OperationGroup],
    ) -> ComplexityLevel:
        """Return the complexity level."""


class GroundTruthGenerator(ABC):
    """Generate reference output and evidence."""

    @abstractmethod
    def generate(
        self,
        context: Context,
        task: Task,
        expected_behaviour: ExpectedBehaviour,
    ) -> tuple[ExpectedOutput, GroundTruth]:
        """Return expected output and ground truth."""


class Validator(ABC):
    """Validate canonical examples."""

    @abstractmethod
    def validate(self, example: CanonicalExample) -> bool:
        """Return whether an example is valid."""


class Exporter(ABC):
    """Convert canonical examples to another format."""

    @abstractmethod
    def export(
        self,
        examples: Iterable[CanonicalExample],
        options: Mapping[str, Any] | None = None,
    ) -> Any:
        """Return exported examples."""


class AIProvider(ABC):
    """Minimal interface for text-based AI provider workflows."""

    @abstractmethod
    def generate(self, prompt: str, response: str | None = None) -> str:
        """Return a text response for a prompt."""
