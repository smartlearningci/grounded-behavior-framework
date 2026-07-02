from enum import Enum


DEFAULT_SCHEMA_VERSION = "1.0"
DEFAULT_CONTEXT_TYPE = "text"


class DecisionType(str, Enum):
    """Context sufficiency decisions defined by the framework."""

    D1_CONTEXT_SUFFICIENT = "D1"
    D2_CONTEXT_INSUFFICIENT = "D2"
    D3_TASK_INCOMPATIBLE = "D3"


class ComplexityLevel(str, Enum):
    """Cognitive complexity levels for canonical examples."""

    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"


class OperationGroup(str, Enum):
    """Top-level context operation groups."""

    O1_LOCALIZE = "O1"
    O2_UNDERSTAND = "O2"
    O3_RELATE = "O3"
    O4_VALIDATE = "O4"
    O5_TRANSFORM = "O5"
    O6_RESTRICT_RESPONSE = "O6"
    O7_EXECUTE_CONTEXT_INSTRUCTIONS = "O7"
