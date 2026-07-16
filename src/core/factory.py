"""Cria os componentes do pipeline a partir da configuração validada."""

from typing import Any

from src.core.config import REQUIRED_PIPELINE_SECTIONS, validate_pipeline_config
from src.core.interfaces import AIProvider
from src.providers.cerebras_provider import CerebrasProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.groq_provider import GroqProvider
from src.providers.manual_provider import ManualProvider
from src.providers.mistral_provider import MistralProvider
from src.providers.openrouter_provider import OpenRouterProvider


def create_component(section_name: str, section_config: dict[str, Any]) -> AIProvider:
    """Cria o provider configurado para uma secção individual do pipeline.

    A seleção é explícita e instancia apenas o provider indicado na secção.
    Valores opcionais de modelo e candidatos são encaminhados sem criar um
    registo dinâmico de providers.
    """
    provider = section_config.get("provider")

    if provider is None:
        raise ValueError(f"Missing provider for pipeline section: {section_name}")

    if provider == "manual":
        return ManualProvider(prompt_path=section_config.get("prompt_path"))
    if provider == "gemini":
        options = {}
        if "model" in section_config:
            options["model"] = section_config["model"]
        return GeminiProvider(**options)
    if provider == "groq":
        return GroqProvider(
            model=section_config.get("model"),
            model_candidates=section_config.get("model_candidates"),
        )
    if provider == "mistral":
        return MistralProvider(
            model=section_config.get("model"),
            model_candidates=section_config.get("model_candidates"),
        )
    if provider == "openrouter":
        return OpenRouterProvider(
            model=section_config.get("model"),
            model_candidates=section_config.get("model_candidates"),
        )
    if provider == "cerebras":
        return CerebrasProvider(
            model=section_config.get("model"),
            model_candidates=section_config.get("model_candidates"),
        )

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
