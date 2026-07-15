"""Carrega e valida os ficheiros YAML que configuram o pipeline."""

from pathlib import Path
from typing import Any

import yaml


REQUIRED_PIPELINE_SECTIONS = (
    "document_loader",
    "context_builder",
    "task_generator",
    "decision_generator",
    "operation_classifier",
    "complexity_classifier",
    "ground_truth_generator",
    "validator",
    "exporter",
)


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Carrega um ficheiro YAML e devolve a sua raiz como dicionário.

    Um ficheiro vazio produz um dicionário vazio. Uma raiz YAML que não seja
    um mapeamento é rejeitada, porque as configurações do projeto são sempre
    representadas por pares chave/valor.
    """
    config_path = Path(path)

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if config is None:
        return {}

    if not isinstance(config, dict):
        raise ValueError("Configuration root must be a mapping.")

    return config


def validate_pipeline_config(config: dict[str, Any]) -> None:
    """Confirma que a configuração contém todas as etapas obrigatórias.

    Não devolve valor quando a configuração é válida. Se faltarem etapas,
    lança ``ValueError`` com a lista das secções em falta.
    """
    missing_sections = [
        section
        for section in REQUIRED_PIPELINE_SECTIONS
        if section not in config
    ]

    if missing_sections:
        missing = ", ".join(missing_sections)
        raise ValueError(f"Missing required pipeline sections: {missing}")


def load_pipeline_config(path: str | Path) -> dict[str, Any]:
    """Carrega uma configuração YAML e valida a estrutura do pipeline.

    Devolve o dicionário validado, pronto para ser entregue à factory de
    componentes. Os erros de leitura ou validação são propagados ao chamador.
    """
    config = load_yaml_config(path)
    validate_pipeline_config(config)
    return config
