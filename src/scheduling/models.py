"""Modelos persistidos pela fila e devolvidos pelo escalonador."""

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone


VALID_JOB_STATUSES = (
    "pending",
    "running",
    "completed",
    "retry_wait",
    "failed",
    "paused",
)
VALID_SCHEDULE_ACTIONS = ("run", "wait", "empty")


def utc_now_iso() -> str:
    """Devolve o instante UTC atual em ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class GenerationJob:
    """Representa um chunk persistente ainda por executar ou já concluído."""

    job_id: str
    matrix_row_id: int
    batch_id: str
    chunk_id: str
    provider: str
    preferred_model: str
    prompt_version: str
    dataset_split_target: str
    examples_requested: int
    prompt_file: str
    metadata_file: str
    status: str
    attempt_count: int
    created_at: str
    updated_at: str
    last_error: str
    result_file: str

    def __post_init__(self) -> None:
        """Valida a representação persistente sem executar lógica de fila."""
        for field_name in (
            "job_id",
            "batch_id",
            "chunk_id",
            "provider",
            "prompt_version",
            "dataset_split_target",
            "prompt_file",
            "metadata_file",
        ):
            if not isinstance(getattr(self, field_name), str) or not getattr(
                self, field_name
            ):
                raise ValueError(f"GenerationJob field '{field_name}' is required")
        if isinstance(self.matrix_row_id, bool) or not isinstance(
            self.matrix_row_id, int
        ):
            raise ValueError("GenerationJob matrix_row_id must be an integer")
        if (
            isinstance(self.examples_requested, bool)
            or not isinstance(self.examples_requested, int)
            or self.examples_requested <= 0
        ):
            raise ValueError("GenerationJob examples_requested must be positive")
        if (
            isinstance(self.attempt_count, bool)
            or not isinstance(self.attempt_count, int)
            or self.attempt_count < 0
        ):
            raise ValueError("GenerationJob attempt_count must be non-negative")
        if self.status not in VALID_JOB_STATUSES:
            raise ValueError(f"Invalid GenerationJob status: {self.status}")
        _validate_utc_timestamp(self.created_at, "created_at")
        _validate_utc_timestamp(self.updated_at, "updated_at")

    def to_dict(self) -> dict[str, object]:
        """Converte o job num dicionário JSON serializável."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "GenerationJob":
        """Reconstrói um job e rejeita campos obrigatórios ausentes."""
        if not isinstance(data, dict):
            raise ValueError("GenerationJob data must be a mapping")
        required = [field.name for field in fields(cls)]
        missing = [field_name for field_name in required if field_name not in data]
        if missing:
            raise ValueError(
                "GenerationJob is missing required fields: " + ", ".join(missing)
            )
        values = {field_name: data[field_name] for field_name in required}
        try:
            return cls(**values)
        except TypeError as exc:
            raise ValueError(f"Malformed GenerationJob: {exc}") from exc


@dataclass
class ScheduleDecision:
    """Descreve a próxima ação sem executar esperas nem providers."""

    job: GenerationJob | None
    action: str
    provider: str | None
    wait_seconds: float
    reason: str

    def __post_init__(self) -> None:
        """Garante ações conhecidas e esperas não negativas."""
        if self.action not in VALID_SCHEDULE_ACTIONS:
            raise ValueError(f"Invalid schedule action: {self.action}")
        if self.wait_seconds < 0:
            raise ValueError("Schedule wait_seconds must be non-negative")


def _validate_utc_timestamp(value: str, field_name: str) -> None:
    """Confirma que um timestamp ISO 8601 representa um instante UTC."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"GenerationJob {field_name} must be a UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"GenerationJob {field_name} must be a UTC timestamp"
        ) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"GenerationJob {field_name} must be a UTC timestamp")
