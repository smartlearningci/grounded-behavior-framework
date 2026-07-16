"""Carrega e valida limites conservadores de execução por provider."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROVIDERS = ("manual", "gemini", "groq", "mistral", "openrouter", "cerebras")


@dataclass
class ProviderLimitConfig:
    """Reúne limites locais configuráveis para um único provider."""

    provider: str
    enabled: bool
    min_delay_seconds: float
    max_requests_per_minute: int | None
    max_requests_per_day: int | None
    max_consecutive_requests: int
    max_job_attempts: int
    cooldown_after_rate_limit_seconds: float

    def __post_init__(self) -> None:
        """Valida tipos, limites positivos e durações não negativas."""
        if self.provider not in PROVIDERS:
            raise ValueError(f"Unknown provider limit section: {self.provider}")
        if not isinstance(self.enabled, bool):
            raise ValueError(f"{self.provider}.enabled must be boolean")
        self.min_delay_seconds = _non_negative_number(
            self.min_delay_seconds,
            f"{self.provider}.min_delay_seconds",
        )
        self.cooldown_after_rate_limit_seconds = _non_negative_number(
            self.cooldown_after_rate_limit_seconds,
            f"{self.provider}.cooldown_after_rate_limit_seconds",
        )
        self.max_requests_per_minute = _optional_positive_integer(
            self.max_requests_per_minute,
            f"{self.provider}.max_requests_per_minute",
        )
        self.max_requests_per_day = _optional_positive_integer(
            self.max_requests_per_day,
            f"{self.provider}.max_requests_per_day",
        )
        self.max_consecutive_requests = _positive_integer(
            self.max_consecutive_requests,
            f"{self.provider}.max_consecutive_requests",
        )
        self.max_job_attempts = _positive_integer(
            self.max_job_attempts,
            f"{self.provider}.max_job_attempts",
        )


def load_provider_limits(
    path: str | Path,
) -> dict[str, ProviderLimitConfig]:
    """Lê YAML e devolve configuração validada para os seis providers."""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Provider limits file does not exist: {config_path}")
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError("Provider limits root must be a mapping")

    unknown = sorted(set(data) - set(PROVIDERS))
    if unknown:
        raise ValueError("Unknown provider limit sections: " + ", ".join(unknown))
    missing = [provider for provider in PROVIDERS if provider not in data]
    if missing:
        raise ValueError("Missing provider limit sections: " + ", ".join(missing))

    configs = {}
    required_fields = {
        "enabled",
        "min_delay_seconds",
        "max_requests_per_minute",
        "max_requests_per_day",
        "max_consecutive_requests",
        "max_job_attempts",
        "cooldown_after_rate_limit_seconds",
    }
    for provider in PROVIDERS:
        values = data[provider]
        if not isinstance(values, dict):
            raise ValueError(f"Provider limits section '{provider}' must be a mapping")
        missing_fields = sorted(required_fields - set(values))
        if missing_fields:
            raise ValueError(
                f"Provider '{provider}' is missing fields: "
                + ", ".join(missing_fields)
            )
        unknown_fields = sorted(set(values) - required_fields)
        if unknown_fields:
            raise ValueError(
                f"Provider '{provider}' has unknown fields: "
                + ", ".join(unknown_fields)
            )
        configs[provider] = ProviderLimitConfig(provider=provider, **values)
    return configs


def _non_negative_number(value: Any, field_name: str) -> float:
    """Normaliza números não negativos sem aceitar booleanos."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative number")
    return float(value)


def _positive_integer(value: Any, field_name: str) -> int:
    """Valida inteiros estritamente positivos sem aceitar booleanos."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _optional_positive_integer(value: Any, field_name: str) -> int | None:
    """Aceita null ou valida um limite inteiro estritamente positivo."""
    if value is None:
        return None
    return _positive_integer(value, field_name)
