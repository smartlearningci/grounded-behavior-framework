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
    """Load a YAML configuration file as a dictionary."""
    config_path = Path(path)

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if config is None:
        return {}

    if not isinstance(config, dict):
        raise ValueError("Configuration root must be a mapping.")

    return config


def validate_pipeline_config(config: dict[str, Any]) -> None:
    """Validate that all required pipeline sections are present."""
    missing_sections = [
        section
        for section in REQUIRED_PIPELINE_SECTIONS
        if section not in config
    ]

    if missing_sections:
        missing = ", ".join(missing_sections)
        raise ValueError(f"Missing required pipeline sections: {missing}")


def load_pipeline_config(path: str | Path) -> dict[str, Any]:
    """Load and validate a pipeline configuration file."""
    config = load_yaml_config(path)
    validate_pipeline_config(config)
    return config
