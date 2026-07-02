from abc import ABC, abstractmethod
from typing import Any, Iterable, Mapping, Sequence

from .constants import Complexity, Decision, Operation
from .schema import (
    Context,
    DatasetExample,
    Document,
    ExpectedBehaviour,
    ExpectedOutput,
    GroundTruth,
    Task,
)


class DocumentLoader(ABC):
    """Load source documents for dataset generation."""

    @abstractmethod
    def load(self, source: str) -> Sequence[Document]:
        """Return documents loaded from a source."""


class ContextBuilder(ABC):
    """Build contexts from source documents."""

    @abstractmethod
    def build(self, documents: Sequence[Document]) -> Sequence[Context]:
        """Return contexts derived from documents."""


class TaskGenerator(ABC):
    """Generate tasks over a context."""

    @abstractmethod
    def generate(self, context: Context) -> Sequence[Task]:
        """Return candidate tasks for a context."""


class DecisionGenerator(ABC):
    """Determine the expected context decision for a task."""

    @abstractmethod
    def decide(self, context: Context, task: Task) -> Decision:
        """Return D1, D2, or D3 for the context/task pair."""


class OperationClassifier(ABC):
    """Classify operations required by a task."""

    @abstractmethod
    def classify(self, context: Context, task: Task) -> Sequence[Operation]:
        """Return one or more operation labels."""


class ComplexityClassifier(ABC):
    """Classify the cognitive complexity of an example."""

    @abstractmethod
    def classify(
        self,
        context: Context,
        task: Task,
        operations: Sequence[Operation],
    ) -> Complexity:
        """Return a complexity level for the context/task pair."""


class GroundTruthGenerator(ABC):
    """Generate reference answers and evidence for evaluation."""

    @abstractmethod
    def generate(
        self,
        context: Context,
        task: Task,
        expected_behaviour: ExpectedBehaviour,
    ) -> tuple[ExpectedOutput, GroundTruth]:
        """Return expected output and evaluation ground truth."""


class Validator(ABC):
    """Validate canonical dataset examples."""

    @abstractmethod
    def validate(self, example: DatasetExample) -> bool:
        """Return whether an example satisfies quality requirements."""


class Exporter(ABC):
    """Convert canonical examples to external dataset formats."""

    @abstractmethod
    def export(
        self,
        examples: Iterable[DatasetExample],
        options: Mapping[str, Any] | None = None,
    ) -> Any:
        """Return examples converted to a target format."""
