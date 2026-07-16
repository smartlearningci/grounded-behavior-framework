"""Modelos dos resultados de validação estrutural."""

from dataclasses import asdict, dataclass, field


VALIDATION_STATUSES = (
    "valid",
    "invalid_json",
    "wrong_example_count",
    "invalid_schema",
    "answer_not_in_context",
    "needs_review",
    "missing_result",
)


@dataclass
class ValidationResult:
    """Regista a validação imutável de um resultado raw."""

    chunk_id: str
    provider: str
    result_file: str
    valid: bool
    status: str
    expected_examples: int
    parsed_examples: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    output_file: str = ""
    validation_timestamp: str = ""

    def __post_init__(self) -> None:
        """Rejeita estados fora do contrato estrutural."""
        if self.status not in VALIDATION_STATUSES:
            raise ValueError(f"Invalid validation status: {self.status}")

    def to_dict(self) -> dict[str, object]:
        """Converte o resultado num dicionário JSON serializável."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ValidationResult":
        """Reconstrói um resultado persistido num sidecar ou relatório."""
        try:
            return cls(**data)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Malformed validation result: {exc}") from exc
