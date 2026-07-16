"""Classifica falhas de execução sem expor credenciais."""

import re
from typing import Any

import requests


MAX_ERROR_LENGTH = 1000
RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


class ExecutionError(Exception):
    """Base das falhas normalizadas pelo executor."""


class ProviderAuthenticationError(ExecutionError):
    """Indica credenciais ausentes ou recusadas."""


class ProviderRateLimitError(ExecutionError):
    """Indica limitação temporária, incluindo Retry-After."""

    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ProviderTemporaryError(ExecutionError):
    """Indica uma falha transitória que pode ser repetida."""


class ProviderPermanentError(ExecutionError):
    """Indica uma falha que não deve ser repetida automaticamente."""


class PromptFileError(ExecutionError):
    """Indica que o prompt não pôde ser lido com segurança."""


class ResultFileError(ExecutionError):
    """Indica que um resultado não pôde ser validado ou persistido."""


def sanitize_error(error: object, limit: int = MAX_ERROR_LENGTH) -> str:
    """Oculta cabeçalhos e tokens óbvios, limitando o texto persistido."""
    text = str(error)
    patterns = (
        (r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+", r"\1[REDACTED]"),
        (r"(?i)(bearer\s+)[^\s,;]+", r"\1[REDACTED]"),
        (r"(?i)((?:api[_-]?key|token|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text[:limit]


def classify_provider_exception(error: Exception) -> ExecutionError:
    """Classifica por estado HTTP, headers e tipos públicos de rede."""
    if isinstance(error, ExecutionError):
        return error
    status = _status_code(error)
    message = sanitize_error(error)
    class_name = type(error).__name__.lower()
    if (
        status in {401, 403}
        or _looks_like_missing_key(error)
        or "authentication" in class_name
        or "permissiondenied" in class_name
    ):
        return ProviderAuthenticationError(message)
    if status == 429 or "ratelimit" in class_name or "rate_limit" in class_name:
        return ProviderRateLimitError(message, _retry_after(error))
    if status in RETRYABLE_STATUS_CODES:
        return ProviderTemporaryError(message)
    if status is not None and 400 <= status < 500:
        return ProviderPermanentError(message)
    if isinstance(error, (TimeoutError, ConnectionError, requests.Timeout, requests.ConnectionError)) or any(
        term in class_name for term in ("timeout", "connection")
    ):
        return ProviderTemporaryError(message)
    return ProviderPermanentError(message)


def _status_code(error: Exception) -> int | None:
    """Obtém um estado HTTP por atributos públicos comuns."""
    direct = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    value = direct if direct is not None else getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def _retry_after(error: Exception) -> float | None:
    """Extrai Retry-After de headers públicos quando está disponível."""
    direct = getattr(error, "retry_after_seconds", None)
    if direct is None:
        direct = getattr(error, "retry_after", None)
    try:
        if direct is not None:
            return max(0.0, float(direct))
    except (TypeError, ValueError):
        pass
    response = getattr(error, "response", None)
    headers: Any = getattr(response, "headers", None)
    if headers is None:
        headers = getattr(error, "headers", None)
    try:
        value = headers.get("Retry-After") if headers is not None else None
        if value is not None:
            return max(0.0, float(value))
    except (TypeError, ValueError):
        pass
    try:
        payload = response.json() if response is not None else {}
        value = payload.get("error", {}).get("metadata", {}).get("retry_after_seconds")
        return max(0.0, float(value)) if value is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def _looks_like_missing_key(error: Exception) -> bool:
    """Reconhece a mensagem pública usada pelos providers existentes."""
    text = str(error).upper()
    return "API_KEY" in text and ("NOT SET" in text or "MISSING" in text)
