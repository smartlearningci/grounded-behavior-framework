"""Testes dos requisitos de carregamento da configuração do pipeline."""

from pathlib import Path

from src.core.config import REQUIRED_PIPELINE_SECTIONS, load_pipeline_config


def test_manual_pipeline_config_has_required_sections():
    """Requisito: o YAML manual deve declarar todas as etapas obrigatórias.

    Resultado esperado: o carregamento é válido e cada secção definida por
    ``REQUIRED_PIPELINE_SECTIONS`` está presente no dicionário resultante.
    """
    config_path = Path("configs/pipeline.manual.yaml")

    config = load_pipeline_config(config_path)

    for section in REQUIRED_PIPELINE_SECTIONS:
        assert section in config
