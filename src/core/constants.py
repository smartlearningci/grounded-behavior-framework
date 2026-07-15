"""Define valores estáveis partilhados pelo schema e pelo pipeline."""

from enum import Enum


DEFAULT_SCHEMA_VERSION = "1.0"
DEFAULT_CONTEXT_TYPE = "text"


class DecisionType(str, Enum):
    """Representa a decisão sobre a adequação do contexto a uma tarefa.

    O resultado é um código textual: contexto suficiente, contexto
    insuficiente ou tarefa incompatível com o contexto disponível.
    """

    D1_CONTEXT_SUFFICIENT = "D1"
    D2_CONTEXT_INSUFFICIENT = "D2"
    D3_TASK_INCOMPATIBLE = "D3"


class ComplexityLevel(str, Enum):
    """Representa o nível de complexidade cognitiva de um exemplo.

    Os valores textuais de C1 a C5 permitem classificar e serializar exemplos
    por dificuldade crescente sem depender de números sem significado.
    """

    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"


class OperationGroup(str, Enum):
    """Identifica as operações de alto nível exigidas por uma tarefa.

    Cada valor textual descreve uma família de operações e pode ser incluído
    nos metadados e no comportamento esperado de um exemplo canónico.
    """

    O1_LOCALIZE = "O1"
    O2_UNDERSTAND = "O2"
    O3_RELATE = "O3"
    O4_VALIDATE = "O4"
    O5_TRANSFORM = "O5"
    O6_RESTRICT_RESPONSE = "O6"
    O7_EXECUTE_CONTEXT_INSTRUCTIONS = "O7"
