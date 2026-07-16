"""Testes do carregamento dos limites locais de providers."""

import copy

import pytest
import yaml

from src.scheduling.config import PROVIDERS, load_provider_limits


def _limits():
    """Cria os seis blocos válidos de configuração."""
    return {
        provider: {
            "enabled": provider != "manual",
            "min_delay_seconds": 6,
            "max_requests_per_minute": None,
            "max_requests_per_day": None,
            "max_consecutive_requests": 1,
            "max_job_attempts": 3,
            "cooldown_after_rate_limit_seconds": 60,
        }
        for provider in PROVIDERS
    }


def _write(path, data):
    """Persiste YAML temporário para o teste."""
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_load_valid_provider_limits_and_null_values(tmp_path):
    """Requisito: YAML completo deve aceitar limites opcionais null.

    Resultado esperado: os seis providers são carregados e manual fica disabled.
    """
    path = tmp_path / "limits.yaml"
    _write(path, _limits())

    configs = load_provider_limits(path)

    assert tuple(configs) == PROVIDERS
    assert configs["gemini"].max_requests_per_minute is None
    assert configs["gemini"].max_requests_per_day is None
    assert configs["manual"].enabled is False


def test_load_provider_limits_rejects_missing_provider(tmp_path):
    """Requisito: todas as seis secções devem existir.

    Resultado esperado: ValueError identifica a secção cerebras removida.
    """
    data = _limits()
    del data["cerebras"]
    path = tmp_path / "limits.yaml"
    _write(path, data)

    with pytest.raises(ValueError, match="cerebras"):
        load_provider_limits(path)


def test_load_provider_limits_rejects_unknown_provider(tmp_path):
    """Requisito: secções de providers desconhecidos são proibidas.

    Resultado esperado: ValueError identifica a secção unknown.
    """
    data = _limits()
    data["unknown"] = copy.deepcopy(data["gemini"])
    path = tmp_path / "limits.yaml"
    _write(path, data)

    with pytest.raises(ValueError, match="unknown"):
        load_provider_limits(path)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("enabled", "yes", "enabled must be boolean"),
        ("min_delay_seconds", -1, "non-negative"),
        ("cooldown_after_rate_limit_seconds", -1, "non-negative"),
        ("max_requests_per_minute", 0, "positive integer"),
        ("max_requests_per_day", 0, "positive integer"),
        ("max_consecutive_requests", 0, "positive integer"),
        ("max_job_attempts", 0, "positive integer"),
    ],
)
def test_load_provider_limits_rejects_invalid_values(
    tmp_path,
    field_name,
    value,
    message,
):
    """Requisito: tipos, durações e contagens devem respeitar limites seguros.

    Resultado esperado: cada valor inválido gera uma mensagem clara.
    """
    data = _limits()
    data["gemini"][field_name] = value
    path = tmp_path / "limits.yaml"
    _write(path, data)

    with pytest.raises(ValueError, match=message):
        load_provider_limits(path)


def test_repository_provider_limits_are_valid():
    """Requisito: a configuração versionada deve respeitar o modelo validado.

    Resultado esperado: seis providers carregam e manual não executa automaticamente.
    """
    configs = load_provider_limits("configs/provider_limits.yaml")

    assert len(configs) == 6
    assert configs["manual"].enabled is False
    assert all(
        configs[provider].max_consecutive_requests == 1
        for provider in PROVIDERS
    )
