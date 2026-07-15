"""Testes dos requisitos de criação de componentes pela factory."""

import pytest

from src.core.config import REQUIRED_PIPELINE_SECTIONS
from src.core.factory import create_pipeline_components
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


def test_unknown_provider_raises_clear_error():
    """Requisito: providers desconhecidos devem ser rejeitados claramente.

    Resultado esperado: a factory lança ``ValueError`` e a mensagem identifica
    tanto a secção ``document_loader`` como o valor inválido ``unknown``.
    """
    config = _manual_config()
    config["document_loader"] = {"provider": "unknown"}

    with pytest.raises(ValueError, match="Unknown provider.*document_loader.*unknown"):
        create_pipeline_components(config)
