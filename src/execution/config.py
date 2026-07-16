"""Carrega a configuração de geração validada nos notebooks."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


RUNTIME_PROVIDERS = ("gemini", "groq", "mistral", "openrouter", "cerebras")
RUNTIME_FIELDS = {
    "system_prompt",
    "temperature",
    "max_tokens",
    "require_json",
    "output_directory",
    "save_prompt_copy",
    "save_raw_metadata",
    "stop_provider_after_consecutive_failures",
}


@dataclass
class ProviderRuntimeConfig:
    """Define os parâmetros de pedido e persistência de um provider."""

    provider: str
    system_prompt: str | None
    temperature: float
    max_tokens: int | None
    require_json: bool
    output_directory: str
    save_prompt_copy: bool
    save_raw_metadata: bool
    stop_provider_after_consecutive_failures: int

    def __post_init__(self) -> None:
        """Valida tipos e valores sem consultar serviços externos."""
        if self.provider not in RUNTIME_PROVIDERS:
            raise ValueError(f"Unknown runtime provider: {self.provider}")
        if self.system_prompt is not None and not isinstance(self.system_prompt, str):
            raise ValueError(f"{self.provider}.system_prompt must be string or null")
        if (
            isinstance(self.temperature, bool)
            or not isinstance(self.temperature, (int, float))
            or self.temperature < 0
        ):
            raise ValueError(f"{self.provider}.temperature must be non-negative")
        self.temperature = float(self.temperature)
        if self.max_tokens is not None and (
            isinstance(self.max_tokens, bool)
            or not isinstance(self.max_tokens, int)
            or self.max_tokens <= 0
        ):
            raise ValueError(f"{self.provider}.max_tokens must be positive or null")
        for field_name in ("require_json", "save_prompt_copy", "save_raw_metadata"):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{self.provider}.{field_name} must be boolean")
        if not isinstance(self.output_directory, str) or not self.output_directory.strip():
            raise ValueError(f"{self.provider}.output_directory must be non-empty")
        if "\x00" in self.output_directory:
            raise ValueError(f"{self.provider}.output_directory is invalid")
        if (
            isinstance(self.stop_provider_after_consecutive_failures, bool)
            or not isinstance(self.stop_provider_after_consecutive_failures, int)
            or self.stop_provider_after_consecutive_failures <= 0
        ):
            raise ValueError(
                f"{self.provider}.stop_provider_after_consecutive_failures "
                "must be positive"
            )


def load_generation_runtime_config(
    path: str | Path,
) -> dict[str, ProviderRuntimeConfig]:
    """Lê YAML e exige uma secção completa por provider API."""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Runtime config does not exist: {config_path}")
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError("Runtime config root must be a mapping")
    unknown = sorted(set(data) - set(RUNTIME_PROVIDERS))
    if unknown:
        raise ValueError("Unknown runtime providers: " + ", ".join(unknown))
    missing = [provider for provider in RUNTIME_PROVIDERS if provider not in data]
    if missing:
        raise ValueError("Missing runtime providers: " + ", ".join(missing))

    configs: dict[str, ProviderRuntimeConfig] = {}
    for provider in RUNTIME_PROVIDERS:
        values = data[provider]
        if not isinstance(values, dict):
            raise ValueError(f"Runtime section '{provider}' must be a mapping")
        missing_fields = sorted(RUNTIME_FIELDS - set(values))
        unknown_fields = sorted(set(values) - RUNTIME_FIELDS)
        if missing_fields:
            raise ValueError(
                f"Runtime provider '{provider}' is missing fields: "
                + ", ".join(missing_fields)
            )
        if unknown_fields:
            raise ValueError(
                f"Runtime provider '{provider}' has unknown fields: "
                + ", ".join(unknown_fields)
            )
        try:
            configs[provider] = ProviderRuntimeConfig(provider=provider, **values)
        except TypeError as exc:
            raise ValueError(f"Malformed runtime provider '{provider}': {exc}") from exc
    return configs
