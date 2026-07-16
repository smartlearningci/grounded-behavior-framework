"""Testes da persistência atómica de resultados brutos."""

import hashlib
import json
import os
from unittest.mock import patch

import pytest

from src.core.interfaces import GenerationRequest, GenerationResult
from src.execution.config import ProviderRuntimeConfig
from src.execution.result_writer import MAX_METADATA_CHARS, ResultWriter
from src.scheduling.models import GenerationJob, utc_now_iso


def _config(tmp_path, save_prompt=True, save_metadata=True):
    return ProviderRuntimeConfig(
        provider="gemini",
        system_prompt=None,
        temperature=0.8,
        max_tokens=None,
        require_json=True,
        output_directory=str(tmp_path / "raw" / "gemini"),
        save_prompt_copy=save_prompt,
        save_raw_metadata=save_metadata,
        stop_provider_after_consecutive_failures=5,
    )


def _job(attempt=1):
    now = utc_now_iso()
    return GenerationJob(
        "job_B0001_C01", 1, "B0001", "B0001_C01", "gemini", "model-a",
        "n1_v1", "train", 20, "B0001_C01.prompt.txt", "meta.json",
        "running", attempt, now, now, "", "",
    )


def test_success_schema_utf8_hash_atomic_and_prompt_copy(tmp_path) -> None:
    """Requisito: resultado completo e atómico. Resultado esperado: schema, UTF-8, hash e cópia."""
    writer = ResultWriter({"gemini": _config(tmp_path)})
    request = GenerationRequest(prompt="instrução", model="model-a", temperature=0.8, require_json=True)
    result = GenerationResult(
        text='{"texto":"olá"}', provider="gemini", requested_model="model-a",
        actual_model="model-v", usage={"tokens": 2}, metadata={"id": "ç"}, attempts=[],
    )
    with patch("src.execution.result_writer.os.replace", wraps=os.replace) as replace:
        path = writer.write_success(
            _job(), request, result, "prompt ç", utc_now_iso(), utc_now_iso()
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["result"]["text"] == '{"texto":"olá"}'
    assert payload["request"]["prompt_sha256"] == hashlib.sha256("prompt ç".encode()).hexdigest()
    assert path.with_name("B0001_C01.prompt.txt").read_text(encoding="utf-8") == "prompt ç"
    assert replace.call_count == 2


def test_success_refuses_overwrite_by_default_and_allows_explicit(tmp_path) -> None:
    """Requisito: overwrite explícito. Resultado esperado: recusa por omissão e substitui com flag."""
    writer = ResultWriter({"gemini": _config(tmp_path, save_prompt=False)})
    request = GenerationRequest(prompt="p")
    first = GenerationResult(text="primeiro", provider="gemini")
    path = writer.write_success(_job(), request, first, "p", utc_now_iso(), utc_now_iso())

    with pytest.raises(FileExistsError):
        writer.write_success(_job(), request, first, "p", utc_now_iso(), utc_now_iso())
    writer.write_success(
        _job(), request, GenerationResult(text="segundo", provider="gemini"),
        "p", utc_now_iso(), utc_now_iso(), overwrite=True,
    )
    assert json.loads(path.read_text())["result"]["text"] == "segundo"


def test_failure_attempts_never_overwrite_and_hide_secrets(tmp_path) -> None:
    """Requisito: falhas versionadas e seguras. Resultado esperado: dois ficheiros sem token."""
    writer = ResultWriter({"gemini": _config(tmp_path)})
    first = writer.write_failure_record(
        _job(), "gemini", "Authorization: Bearer top-secret", utc_now_iso(), utc_now_iso()
    )
    second = writer.write_failure_record(
        _job(), "gemini", "api_key=hidden", utc_now_iso(), utc_now_iso()
    )

    assert first != second and first.exists() and second.exists()
    combined = first.read_text() + second.read_text()
    assert "top-secret" not in combined and "hidden" not in combined
    assert "[REDACTED]" in combined


def test_metadata_is_bounded_and_sensitive_keys_are_redacted(tmp_path) -> None:
    """Requisito: metadados limitados. Resultado esperado: volume truncado e chaves secretas ocultas."""
    writer = ResultWriter({"gemini": _config(tmp_path, save_prompt=False)})
    result = GenerationResult(
        text="raw", provider="gemini",
        metadata={"Authorization": "Bearer secret", "large": "x" * (MAX_METADATA_CHARS + 10)},
    )
    path = writer.write_success(
        _job(), GenerationRequest(prompt="p"), result, "p", utc_now_iso(), utc_now_iso()
    )
    metadata = json.loads(path.read_text())["result"]["metadata"]

    assert len(json.dumps(metadata)) < MAX_METADATA_CHARS
    assert "secret" not in json.dumps(metadata)
