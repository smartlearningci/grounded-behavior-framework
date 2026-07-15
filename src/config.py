"""Disponibiliza os caminhos principais usados pelos recursos do projeto."""

from pathlib import Path

# Raiz calculada a partir deste ficheiro para evitar caminhos absolutos locais.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Diretórios convencionais onde o projeto guarda dados, prompts e notebooks.
DATASETS = PROJECT_ROOT / "datasets"
PROMPTS = PROJECT_ROOT / "prompts"
NOTEBOOKS = PROJECT_ROOT / "notebooks"
