"""Escreve sidecars e relatórios de validação atomicamente."""

import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from .models import ValidationResult


def write_validation_sidecar(
    result: ValidationResult,
    path: str | Path,
    overwrite: bool = False,
) -> Path:
    """Publica um sidecar JSON sem substituir implicitamente um anterior."""
    destination = Path(path)
    result.output_file = str(destination)
    _atomic_text(
        destination,
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
        overwrite,
    )
    return destination


def write_validation_report(
    results: list[ValidationResult],
    path: str | Path,
    overwrite: bool = False,
) -> Path:
    """Escreve JSONL ordenado com um registo por resultado validado."""
    content = "".join(
        json.dumps(result.to_dict(), ensure_ascii=False) + "\n" for result in results
    )
    destination = Path(path)
    _atomic_text(destination, content, overwrite)
    return destination


def validation_summary(results: list[ValidationResult]) -> dict[str, object]:
    """Conta estados e providers para apresentação e auditoria."""
    statuses = Counter(result.status for result in results)
    providers = Counter(result.provider for result in results)
    return {
        "files_checked": len(results),
        "valid": statuses["valid"],
        "invalid_json": statuses["invalid_json"],
        "wrong_example_count": statuses["wrong_example_count"],
        "invalid_schema": statuses["invalid_schema"],
        "answer_not_in_context": statuses["answer_not_in_context"],
        "needs_review": statuses["needs_review"],
        "missing_result": statuses["missing_result"],
        "providers": dict(providers),
    }


def _atomic_text(path: Path, content: str, overwrite: bool) -> None:
    """Publica texto UTF-8 por rename no diretório de destino."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Validation output already exists: {path}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as file:
            file.write(content)
            temporary = Path(file.name)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Validation output already exists: {path}")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
