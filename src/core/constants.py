from enum import Enum


DEFAULT_SCHEMA_VERSION = "1.0"
DEFAULT_CONTEXT_MODALITY = "text"


class Decision(str, Enum):
    """Possible context sufficiency decisions."""

    CONTEXT_SUFFICIENT = "D1"
    CONTEXT_INSUFFICIENT = "D2"
    TASK_INCOMPATIBLE = "D3"


class Operation(str, Enum):
    """Context operations and suboperations supported by the framework."""

    LOCATE_INFORMATION = "O1"
    IDENTIFY_ENTITIES = "O1.1"
    IDENTIFY_VALUES = "O1.2"
    IDENTIFY_FACTS = "O1.3"
    IDENTIFY_EXPLICIT_RELATIONS = "O1.4"

    UNDERSTAND_INFORMATION = "O2"
    EXPLAIN = "O2.1"
    INTERPRET = "O2.2"
    CLASSIFY = "O2.3"
    COMPARE = "O2.4"

    RELATE_INFORMATION = "O3"
    INTEGRATE_FACTS = "O3.1"
    RELATE_ENTITIES = "O3.2"
    ORDER = "O3.3"
    IDENTIFY_DEPENDENCIES = "O3.4"

    VALIDATE_INFORMATION = "O4"
    CONFIRM = "O4.1"
    REFUTE = "O4.2"
    JUSTIFY = "O4.3"
    DETECT_INCONSISTENCIES = "O4.4"

    TRANSFORM_INFORMATION = "O5"
    SUMMARIZE = "O5.1"
    REFORMULATE = "O5.2"
    SIMPLIFY = "O5.3"
    STRUCTURE = "O5.4"
    EXTRACT = "O5.5"

    RESTRICT_RESPONSE = "O6"
    LIMIT_LENGTH = "O6.1"
    CONTROL_FORMAT = "O6.2"
    CONTROL_LANGUAGE = "O6.3"
    CLOSED_RESPONSE = "O6.4"

    EXECUTE_CONTEXT_INSTRUCTIONS = "O7"
    SELECT_SECTIONS = "O7.1"
    IGNORE_INFORMATION = "O7.2"
    APPLY_RULES = "O7.3"
    COMBINE_INSTRUCTIONS = "O7.4"


class Complexity(str, Enum):
    """Cognitive complexity levels for dataset examples."""

    VERY_LOW = "C1"
    LOW = "C2"
    MEDIUM = "C3"
    HIGH = "C4"
    VERY_HIGH = "C5"
