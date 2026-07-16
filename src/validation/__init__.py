"""Validação estrutural imutável dos resultados de geração."""

from .models import ValidationResult
from .result_validator import missing_result, validate_result_file

__all__ = ["ValidationResult", "missing_result", "validate_result_file"]
