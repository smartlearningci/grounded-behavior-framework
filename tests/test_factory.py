"""Testes dos requisitos de criação de componentes pela factory."""

from unittest.mock import Mock

import pytest

from src.core.config import REQUIRED_PIPELINE_SECTIONS
from src.core.factory import create_component, create_pipeline_components
from src.providers.manual_provider import ManualProvider


def _manual_config():
    """Cria uma configuração válida com o provider manual em todas as etapas."""
    return {
        section: {"provider": "manual"}
        for section in REQUIRED_PIPELINE_SECTIONS
    }


def test_create_manual_pipeline_components():
    """Requisito: a factory deve construir todo o pipeline manual.

    Resultado esperado: existe um componente para cada secção obrigatória e
    todos os componentes devolvidos são instâncias de ``ManualProvider``.
    """
    components = create_pipeline_components(_manual_config())

    assert set(components) == set(REQUIRED_PIPELINE_SECTIONS)
    assert all(
        isinstance(component, ManualProvider)
        for component in components.values()
    )


@pytest.mark.parametrize(
    ("provider_name", "constructor_name"),
    [
        ("gemini", "GeminiProvider"),
        ("groq", "GroqProvider"),
        ("mistral", "MistralProvider"),
        ("openrouter", "OpenRouterProvider"),
        ("cerebras", "CerebrasProvider"),
    ],
)
def test_create_api_provider_lazily_with_configuration(
    provider_name,
    constructor_name,
    monkeypatch,
):
    """Requisito: a factory deve criar apenas o provider API selecionado.

    Resultado esperado: o construtor escolhido recebe modelo e candidatos
    suportados sem instanciar qualquer outro provider.
    """
    constructors = {}
    for name in (
        "GeminiProvider",
        "GroqProvider",
        "MistralProvider",
        "OpenRouterProvider",
        "CerebrasProvider",
    ):
        constructor = constructors[name] = Mock(name=name)
        monkeypatch.setattr(f"src.core.factory.{name}", constructor)

    config = {
        "provider": provider_name,
        "model": "configured-model",
        "model_candidates": ["candidate-a", "candidate-b"],
    }

    result = create_component("task_generator", config)

    selected = constructors[constructor_name]
    assert result is selected.return_value
    if provider_name == "gemini":
        selected.assert_called_once_with(model="configured-model")
    else:
        selected.assert_called_once_with(
            model="configured-model",
            model_candidates=["candidate-a", "candidate-b"],
        )
    for name, constructor in constructors.items():
        if name != constructor_name:
            constructor.assert_not_called()


def test_create_manual_provider_passes_prompt_path(tmp_path):
    """Requisito: a factory deve encaminhar o caminho do prompt manual.

    Resultado esperado: ManualProvider conserva exatamente o caminho configurado.
    """
    prompt_path = tmp_path / "prompt.txt"

    provider = create_component(
        "task_generator",
        {"provider": "manual", "prompt_path": prompt_path},
    )

    assert isinstance(provider, ManualProvider)
    assert provider.prompt_path == prompt_path


def test_unknown_provider_raises_clear_error():
    """Requisito: providers desconhecidos devem ser rejeitados claramente.

    Resultado esperado: a factory lança ``ValueError`` e a mensagem identifica
    tanto a secção ``document_loader`` como o valor inválido ``unknown``.
    """
    config = _manual_config()
    config["document_loader"] = {"provider": "unknown"}

    with pytest.raises(ValueError, match="Unknown provider.*document_loader.*unknown"):
        create_pipeline_components(config)
