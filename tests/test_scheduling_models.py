"""Testes dos modelos persistentes e decisões do escalonador."""

from datetime import datetime, timezone

import pytest

from src.scheduling.models import (
    GenerationJob,
    ScheduleDecision,
    utc_now_iso,
)


def _job_data(**overrides):
    """Cria um dicionário completo para GenerationJob."""
    timestamp = utc_now_iso()
    data = {
        "job_id": "job_B0001_C01",
        "matrix_row_id": 1,
        "batch_id": "B0001",
        "chunk_id": "B0001_C01",
        "provider": "gemini",
        "preferred_model": "model-a",
        "prompt_version": "prompt_v1",
        "dataset_split_target": "train",
        "examples_requested": 20,
        "prompt_file": "B0001_C01.prompt.txt",
        "metadata_file": "B0001_C01.metadata.json",
        "status": "pending",
        "attempt_count": 0,
        "created_at": timestamp,
        "updated_at": timestamp,
        "last_error": "",
        "result_file": "",
    }
    data.update(overrides)
    return data


def test_generation_job_serialization_round_trip():
    """Requisito: GenerationJob deve serializar e restaurar sem perdas.

    Resultado esperado: to_dict e from_dict produzem um job exatamente igual.
    """
    job = GenerationJob(**_job_data())

    restored = GenerationJob.from_dict(job.to_dict())

    assert restored == job


def test_generation_job_timestamps_are_utc_iso8601():
    """Requisito: timestamps persistentes devem representar instantes UTC.

    Resultado esperado: utc_now_iso inclui timezone e é aceite pelo modelo.
    """
    value = utc_now_iso()
    parsed = datetime.fromisoformat(value)

    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)
    assert GenerationJob(**_job_data(created_at=value, updated_at=value))


@pytest.mark.parametrize(
    "status",
    ["pending", "running", "completed", "retry_wait", "failed", "paused"],
)
def test_generation_job_accepts_all_valid_statuses(status):
    """Requisito: os seis estados resumíveis devem ser aceites.

    Resultado esperado: cada estado definido constrói um GenerationJob válido.
    """
    assert GenerationJob(**_job_data(status=status)).status == status


def test_generation_job_rejects_invalid_status():
    """Requisito: estados desconhecidos não podem entrar na fila.

    Resultado esperado: ValueError identifica o estado inválido.
    """
    with pytest.raises(ValueError, match="Invalid GenerationJob status"):
        GenerationJob(**_job_data(status="unknown"))


def test_generation_job_from_dict_rejects_missing_fields():
    """Requisito: todos os campos persistentes são obrigatórios.

    Resultado esperado: ValueError enumera result_file quando este está ausente.
    """
    data = _job_data()
    del data["result_file"]

    with pytest.raises(ValueError, match="result_file"):
        GenerationJob.from_dict(data)


def test_schedule_decision_validates_action_and_wait():
    """Requisito: decisões aceitam apenas run, wait e empty sem espera negativa.

    Resultado esperado: ações inválidas e waits negativos provocam ValueError.
    """
    job = GenerationJob(**_job_data())
    assert ScheduleDecision(job, "run", "gemini", 0, "ready")

    with pytest.raises(ValueError, match="Invalid schedule action"):
        ScheduleDecision(None, "unknown", None, 0, "invalid")
    with pytest.raises(ValueError, match="non-negative"):
        ScheduleDecision(None, "wait", None, -1, "invalid")
