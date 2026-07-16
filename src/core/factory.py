"""Cria os componentes do pipeline a partir da configuração validada."""

from typing import Any

from src.core.config import REQUIRED_PIPELINE_SECTIONS, validate_pipeline_config
from src.core.interfaces import AIProvider
from src.providers.manual_provider import ManualProvider


def create_component(section_name: str, section_config: dict[str, Any]) -> AIProvider:
    """Cria o provider configurado para uma secção individual do pipeline.

    Atualmente só o provider manual está registado. Devolve uma instância de
    ``ManualProvider`` ou lança ``ValueError`` quando o nome está ausente ou
    ainda não é reconhecido pela factory.
    """
    provider = section_config.get("provider")

    if provider is None:
        raise ValueError(f"Missing provider for pipeline section: {section_name}")

    if provider == "manual":
        return ManualProvider()

    raise ValueError(
        f"Unknown provider for pipeline section '{section_name}': {provider}"
    )


def create_pipeline_components(config: dict[str, Any]) -> dict[str, AIProvider]:
    """Constrói todos os componentes obrigatórios de um pipeline.

    Valida primeiro as secções da configuração e devolve um dicionário que
    associa cada nome de etapa à respetiva instância de provider.
    """
    validate_pipeline_config(config)

    return {
        section: create_component(section, config[section])
        for section in REQUIRED_PIPELINE_SECTIONS
    }
