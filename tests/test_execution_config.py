"""Testes da configuração runtime dos providers."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from src.execution.config import RUNTIME_PROVIDERS, load_generation_runtime_config


SOURCE = Path("configs/generation_runtime.yaml")


def _data():
    return yaml.safe_load(SOURCE.read_text(encoding="utf-8"))


def _write(path, data) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_valid_runtime_config_matches_notebook_settings() -> None:
    """Requisito: YAML válido. Resultado esperado: cinco providers e limites validados."""
    configs = load_generation_runtime_config(SOURCE)

    assert tuple(configs) == RUNTIME_PROVIDERS
    assert configs["gemini"].max_tokens is None
    assert configs["gemini"].system_prompt is None
    assert all(config.temperature == 0.8 for config in configs.values())
    assert all(config.require_json for config in configs.values())


def test_missing_and_unknown_provider_are_rejected(tmp_path) -> None:
    """Requisito: providers completos. Resultado esperado: secções em falta ou extra falham."""
    data = _data()
    del data["groq"]
    path = tmp_path / "missing.yaml"
    _write(path, data)
    with pytest.raises(ValueError, match="Missing.*groq"):
        load_generation_runtime_config(path)

    data = _data()
    data["unknown"] = deepcopy(data["gemini"])
    _write(path, data)
    with pytest.raises(ValueError, match="Unknown.*unknown"):
        load_generation_runtime_config(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("require_json", "yes", "boolean"),
        ("save_prompt_copy", 1, "boolean"),
        ("temperature", -0.1, "non-negative"),
        ("max_tokens", 0, "positive or null"),
        ("output_directory", "", "non-empty"),
        ("stop_provider_after_consecutive_failures", 0, "positive"),
    ],
)
def test_invalid_runtime_values_are_rejected(tmp_path, field, value, message) -> None:
    """Requisito: tipos e limites corretos. Resultado esperado: ValueError identifica o campo."""
    data = _data()
    data["gemini"][field] = value
    path = tmp_path / "invalid.yaml"
    _write(path, data)

    with pytest.raises(ValueError, match=message):
        load_generation_runtime_config(path)


def test_null_max_tokens_is_supported(tmp_path) -> None:
    """Requisito: max_tokens opcional. Resultado esperado: null permanece None."""
    data = _data()
    data["groq"]["max_tokens"] = None
    path = tmp_path / "runtime.yaml"
    _write(path, data)

    assert load_generation_runtime_config(path)["groq"].max_tokens is None
