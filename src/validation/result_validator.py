"""Valida envelopes raw e o payload estrutural gerado."""

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from .models import ValidationResult
from .parser import parse_generated_json


OUTER_KEYS = {"job", "request", "result", "execution"}
EXAMPLE_KEYS = {"context", "question", "answer"}


def validate_result_file(result_path: str | Path) -> ValidationResult:
    """Valida sem escrever, corrigir ou alterar o resultado raw recebido."""
    path = Path(result_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        outer = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return ValidationResult(
            "", "", str(path), False, "invalid_json", 0, 0,
            [f"Outer execution result is invalid JSON: {exc}"], [], "", timestamp,
        )
    if not isinstance(outer, dict):
        return _result(outer, path, False, "invalid_schema", 0, ["Outer result must be an object"], [])
    missing_outer = sorted(OUTER_KEYS - set(outer))
    if missing_outer:
        return _result(
            outer, path, False, "invalid_schema", 0,
            ["Missing outer keys: " + ", ".join(missing_outer)], [],
        )
    job = outer.get("job")
    result = outer.get("result")
    if not isinstance(job, dict) or not isinstance(result, dict):
        return _result(outer, path, False, "invalid_schema", 0, ["job and result must be objects"], [])
    text = result.get("text")
    if not isinstance(text, str) or not text.strip():
        return _result(outer, path, False, "invalid_schema", 0, ["result.text must be a non-empty string"], [])
    payload, parse_error, warnings = parse_generated_json(text)
    if parse_error is not None:
        return _result(outer, path, False, "invalid_json", 0, [parse_error], warnings)
    if not isinstance(payload, dict) or set(payload) != {"examples"}:
        return _result(
            outer, path, False, "invalid_schema", 0,
            ["Generated payload must be an object containing only 'examples'"], warnings,
        )
    examples = payload.get("examples")
    if not isinstance(examples, list):
        return _result(outer, path, False, "invalid_schema", 0, ["examples must be an array"], warnings)
    parsed_count = len(examples)
    errors: list[str] = []
    grounding_errors: list[str] = []
    for index, example in enumerate(examples, start=1):
        if not isinstance(example, dict):
            errors.append(f"Example {index} must be an object")
            continue
        missing = sorted(EXAMPLE_KEYS - set(example))
        if missing:
            errors.append(f"Example {index} is missing fields: {', '.join(missing)}")
            continue
        for field_name in EXAMPLE_KEYS:
            value = example[field_name]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"Example {index} field '{field_name}' must be a non-empty string")
        if not errors or not any(item.startswith(f"Example {index} ") for item in errors):
            if _normalise(example["answer"]) not in _normalise(example["context"]):
                grounding_errors.append(f"Example {index} answer is not present in context")
    if errors:
        return _result(outer, path, False, "invalid_schema", parsed_count, errors, warnings)
    expected = _expected(outer)
    if parsed_count != expected:
        return _result(
            outer, path, False, "wrong_example_count", parsed_count,
            [f"Expected {expected} examples, found {parsed_count}"], warnings,
        )
    if grounding_errors:
        return _result(
            outer, path, False, "answer_not_in_context", parsed_count,
            grounding_errors, warnings,
        )
    return _result(outer, path, True, "valid", parsed_count, [], warnings)


def missing_result(
    chunk_id: str,
    provider: str,
    result_path: str | Path,
    expected_examples: int,
) -> ValidationResult:
    """Cria um resultado explícito para um ficheiro esperado ausente."""
    return ValidationResult(
        chunk_id, provider, str(result_path), False, "missing_result",
        expected_examples, 0, ["Expected raw result file is missing"], [], "",
        datetime.now(timezone.utc).isoformat(),
    )


def _result(
    outer: object,
    path: Path,
    valid: bool,
    status: str,
    parsed: int,
    errors: list[str],
    warnings: list[str],
) -> ValidationResult:
    """Extrai metadados seguros do envelope, mesmo quando incompleto."""
    job = outer.get("job", {}) if isinstance(outer, dict) else {}
    if not isinstance(job, dict):
        job = {}
    return ValidationResult(
        str(job.get("chunk_id", "")),
        str(job.get("provider", "")),
        str(path),
        valid,
        status,
        _expected(outer),
        parsed,
        errors,
        warnings,
        "",
        datetime.now(timezone.utc).isoformat(),
    )


def _expected(outer: object) -> int:
    """Obtém a cardinalidade esperada sem aceitar booleanos."""
    if not isinstance(outer, dict) or not isinstance(outer.get("job"), dict):
        return 0
    value = outer["job"].get("examples_requested", 0)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _normalise(value: str) -> str:
    """Normaliza Unicode, caixa, espaços e pontuação periférica."""
    text = unicodedata.normalize("NFKC", value).casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .,:;!?\"'()[]{}")
