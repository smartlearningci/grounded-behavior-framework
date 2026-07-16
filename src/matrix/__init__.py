"""Leitura e representação das linhas da matriz de capacidades."""

from .models import MatrixRow
from .reader import read_matrix, validate_matrix_rows

__all__ = ["MatrixRow", "read_matrix", "validate_matrix_rows"]
