"""Persiste resultados brutos e tentativas falhadas de forma atómica."""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.interfaces import GenerationRequest, GenerationResult
from src.scheduling.models import GenerationJob

from .config import ProviderRuntimeConfig
from .errors import ResultFileError, sanitize_error


MAX_METADATA_CHARS = 50_000


class ResultWriter:
    """Escreve artefactos por provider sem analisar o JSON gerado."""

    def __init__(self, runtime_configs: dict[str, ProviderRuntimeConfig]) -> None:
        """Recebe os destinos e opções já validados."""
        self.runtime_configs = runtime_configs

    def success_path(self, job: GenerationJob) -> Path:
        """Calcula o caminho esperado do resultado concluído."""
        return Path(self._config(job.provider).output_directory) / (
            f"{job.chunk_id}.result.json"
        )

    def write_success(
        self,
        job: GenerationJob,
        request: GenerationRequest,
        result: GenerationResult,
        prompt_text: str,
        started_at: str,
        completed_at: str,
        overwrite: bool = False,
    ) -> Path:
        """Guarda texto e proveniência sem alterar o conteúdo devolvido."""
        path = self.success_path(job)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Successful result already exists: {path}")
        config = self._config(job.provider)
        payload = {
            "schema_version": "1.0",
            "job": {
                "job_id": job.job_id,
                "matrix_row_id": job.matrix_row_id,
                "batch_id": job.batch_id,
                "chunk_id": job.chunk_id,
                "provider": job.provider,
                "preferred_model": job.preferred_model,
                "prompt_version": job.prompt_version,
                "dataset_split_target": job.dataset_split_target,
                "examples_requested": job.examples_requested,
                "attempt_count": job.attempt_count,
            },
            "request": {
                "system_prompt": request.system_prompt,
                "requested_model": request.model,
                "model_candidates": list(request.model_candidates),
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "require_json": request.require_json,
                "prompt_file": job.prompt_file,
                "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
            },
            "result": {
                "text": result.text,
                "provider": result.provider,
                "requested_model": result.requested_model,
                "actual_model": result.actual_model,
                "usage": _bounded(result.usage) if config.save_raw_metadata else {},
                "metadata": _bounded(result.metadata) if config.save_raw_metadata else {},
                "attempts": _bounded(result.attempts) if config.save_raw_metadata else [],
            },
            "execution": {
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_seconds": _duration(started_at, completed_at),
            },
        }
        if config.save_prompt_copy:
            _atomic_text(
                path.with_name(f"{job.chunk_id}.prompt.txt"),
                prompt_text,
                overwrite=overwrite,
            )
        _atomic_json(path, payload, overwrite=overwrite)
        return path

    def write_failure_record(
        self,
        job: GenerationJob,
        provider: str,
        error: object,
        started_at: str,
        completed_at: str,
    ) -> Path:
        """Acrescenta uma tentativa falhada sem substituir tentativas anteriores."""
        directory = Path(self._config(provider).output_directory) / "attempts"
        base = directory / f"{job.chunk_id}.attempt-{job.attempt_count}.failure.json"
        path = _unused_version(base)
        payload = {
            "schema_version": "1.0",
            "job_id": job.job_id,
            "chunk_id": job.chunk_id,
            "provider": provider,
            "attempt_count": job.attempt_count,
            "error": sanitize_error(error),
            "execution": {
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_seconds": _duration(started_at, completed_at),
            },
        }
        _atomic_json(path, payload, overwrite=False)
        return path

    def _config(self, provider: str) -> ProviderRuntimeConfig:
        """Obtém a configuração de um provider conhecido."""
        try:
            return self.runtime_configs[provider]
        except KeyError as exc:
            raise ResultFileError(f"Missing runtime config for provider: {provider}") from exc


def validate_existing_result(path: Path) -> None:
    """Confirma que um resultado existente contém JSON e o esquema base."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ResultFileError(f"Existing result is not valid JSON: {path}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != "1.0":
        raise ResultFileError(f"Existing result has an invalid schema: {path}")


def _atomic_json(path: Path, payload: object, overwrite: bool) -> None:
    """Publica JSON UTF-8 por rename atómico no mesmo filesystem."""
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _atomic_text(path, text, overwrite)


def _atomic_text(path: Path, text: str, overwrite: bool) -> None:
    """Escreve texto num temporário e publica-o sem perda parcial."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Result artifact already exists: {path}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            file.write(text)
            temporary = Path(file.name)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Result artifact already exists: {path}")
        os.replace(temporary, path)
    except (OSError, UnicodeError) as exc:
        raise ResultFileError(f"Could not write result artifact: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _unused_version(base: Path) -> Path:
    """Escolhe um nome livre, versionando colisões da mesma tentativa."""
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = base.with_name(base.name.replace(".failure.json", f"-{index}.failure.json"))
        if not candidate.exists():
            return candidate
        index += 1


def _duration(started_at: str, completed_at: str) -> float:
    """Calcula uma duração ISO não negativa."""
    try:
        return max(0.0, (datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)).total_seconds())
    except (TypeError, ValueError):
        return 0.0


def _bounded(value: object) -> object:
    """Normaliza, sanitiza e limita metadados potencialmente volumosos."""
    plain = _plain(value)
    encoded = json.dumps(plain, ensure_ascii=False)
    if len(encoded) <= MAX_METADATA_CHARS:
        return plain
    return {"truncated": True, "preview": sanitize_error(encoded, MAX_METADATA_CHARS)}


def _plain(value: object) -> object:
    """Converte objetos comuns numa representação JSON sem secrets."""
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for key, item in value.items():
            label = str(key)
            if any(term in label.lower() for term in ("authorization", "api_key", "apikey", "secret", "token")):
                result[label] = "[REDACTED]"
            else:
                result[label] = _plain(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return sanitize_error(value) if isinstance(value, str) else value
    return sanitize_error(repr(value))
