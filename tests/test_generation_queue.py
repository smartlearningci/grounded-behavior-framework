"""Testes da fila JSONL persistente e da conversão do manifesto."""

import json
import os
from unittest.mock import patch

import pytest

from src.scheduling.models import GenerationJob, utc_now_iso
from src.scheduling.queue import GenerationQueue, build_jobs_from_manifest


def _job(number=1, provider="gemini", status="pending", chunk_id=None):
    """Cria um job válido para persistência temporária."""
    chunk = chunk_id or f"B{number:04d}_C01"
    timestamp = utc_now_iso()
    return GenerationJob(
        job_id=f"job_{chunk}",
        matrix_row_id=number,
        batch_id=f"B{number:04d}",
        chunk_id=chunk,
        provider=provider,
        preferred_model="model-a",
        prompt_version="prompt_v1",
        dataset_split_target="train",
        examples_requested=20,
        prompt_file=f"{chunk}.prompt.txt",
        metadata_file=f"{chunk}.metadata.json",
        status=status,
        attempt_count=0,
        created_at=timestamp,
        updated_at=timestamp,
        last_error="",
        result_file="",
    )


def _manifest_entry(number=1, provider="gemini", chunk_id=None):
    """Cria uma entrada mínima do manifesto de prompts."""
    chunk = chunk_id or f"B{number:04d}_C01"
    return {
        "matrix_row_id": number,
        "batch_id": f"B{number:04d}",
        "chunk_id": chunk,
        "assigned_provider": provider,
        "preferred_model": "model-a",
        "prompt_version": "prompt_v1",
        "dataset_split_target": "train",
        "examples_per_prompt": 20,
        "prompt_file": f"{chunk}.prompt.txt",
        "metadata_file": f"{chunk}.metadata.json",
    }


def _write_manifest(path, entries):
    """Escreve entradas JSONL para testar a conversão."""
    path.write_text(
        "".join(json.dumps(entry) + "\n" for entry in entries),
        encoding="utf-8",
    )


def test_build_jobs_from_manifest_preserves_order_and_relative_paths(tmp_path):
    """Requisito: cada entrada deve originar um job pending pela mesma ordem.

    Resultado esperado: IDs são determinísticos e caminhos continuam relativos.
    """
    manifest = tmp_path / "manifest.jsonl"
    _write_manifest(
        manifest,
        [_manifest_entry(2, "groq"), _manifest_entry(1, "gemini")],
    )

    jobs = build_jobs_from_manifest(manifest)

    assert [job.job_id for job in jobs] == ["job_B0002_C01", "job_B0001_C01"]
    assert [job.provider for job in jobs] == ["groq", "gemini"]
    assert all(job.status == "pending" and job.attempt_count == 0 for job in jobs)
    assert jobs[0].prompt_file == "B0002_C01.prompt.txt"


def test_build_jobs_rejects_missing_fields_and_duplicate_chunks(tmp_path):
    """Requisito: manifesto exige campos completos e chunk_id único.

    Resultado esperado: ambas as formas inválidas provocam ValueError claro.
    """
    manifest = tmp_path / "manifest.jsonl"
    incomplete = _manifest_entry()
    del incomplete["preferred_model"]
    _write_manifest(manifest, [incomplete])
    with pytest.raises(ValueError, match="preferred_model"):
        build_jobs_from_manifest(manifest)

    duplicate = _manifest_entry()
    _write_manifest(manifest, [duplicate, duplicate])
    with pytest.raises(ValueError, match="Duplicate manifest chunk_id"):
        build_jobs_from_manifest(manifest)


def test_queue_load_save_preserves_order_and_uses_atomic_replace(tmp_path):
    """Requisito: save deve ser atómico e load deve preservar a ordem.

    Resultado esperado: os jobs regressam na mesma ordem e os.replace é usado.
    """
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    jobs = [_job(2, "groq"), _job(1, "gemini")]

    with patch("src.scheduling.queue.os.replace", wraps=os.replace) as replace:
        queue.save(jobs)

    assert replace.call_count == 1
    assert queue.load() == jobs


def test_queue_add_jobs_does_not_lose_existing_jobs(tmp_path):
    """Requisito: add_jobs deve acrescentar sem apagar jobs existentes.

    Resultado esperado: o job inicial permanece antes do job novo.
    """
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    queue.save([_job(1)])

    queue.add_jobs([_job(2, "groq")])

    assert [job.job_id for job in queue.load()] == [
        "job_B0001_C01",
        "job_B0002_C01",
    ]


@pytest.mark.parametrize("duplicate_kind", ["job_id", "chunk_id"])
def test_queue_rejects_duplicate_jobs_and_chunks(tmp_path, duplicate_kind):
    """Requisito: job_id e chunk_id devem ser únicos em toda a fila.

    Resultado esperado: o tipo de duplicado selecionado provoca ValueError.
    """
    first = _job(1)
    second = _job(2)
    setattr(second, duplicate_kind, getattr(first, duplicate_kind))
    queue = GenerationQueue(tmp_path / "jobs.jsonl")

    with pytest.raises(ValueError, match=f"Duplicate queue {duplicate_kind}"):
        queue.save([first, second])


def test_queue_malformed_jsonl_reports_line_number(tmp_path):
    """Requisito: JSONL malformado deve identificar a linha exata.

    Resultado esperado: ValueError aponta para a segunda linha inválida.
    """
    path = tmp_path / "jobs.jsonl"
    path.write_text(json.dumps(_job(1).to_dict()) + "\n{bad\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        GenerationQueue(path).load()


def test_missing_queue_is_empty_and_status_filter_works(tmp_path):
    """Requisito: fila ausente é vazia e get_jobs pode filtrar estado.

    Resultado esperado: load devolve vazio e apenas o job failed é filtrado.
    """
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    assert queue.load() == []
    queue.save([_job(1), _job(2, status="failed")])

    assert [job.job_id for job in queue.get_jobs("failed")] == ["job_B0002_C01"]


def test_queue_reset_running_jobs_and_summary(tmp_path):
    """Requisito: jobs running devem ser recuperáveis após interrupção.

    Resultado esperado: dois jobs voltam a pending e o resumo inclui zeros.
    """
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    queue.save([_job(1, status="running"), _job(2, status="running"), _job(3)])

    changed = queue.reset_running_jobs()

    assert changed == 2
    assert queue.summary() == {
        "pending": 3,
        "running": 0,
        "completed": 0,
        "retry_wait": 0,
        "failed": 0,
        "paused": 0,
    }


def test_queue_update_changes_timestamp_and_missing_job_fails(tmp_path):
    """Requisito: update deve atualizar jobs existentes e rejeitar ausentes.

    Resultado esperado: estado/timestamp persistem e job desconhecido gera KeyError.
    """
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    job = _job(1)
    old_timestamp = job.updated_at
    queue.save([job])
    job.status = "paused"

    queue.update_job(job)

    restored = queue.load()[0]
    assert restored.status == "paused"
    assert restored.updated_at >= old_timestamp
    with pytest.raises(KeyError, match="does not exist"):
        queue.update_job(_job(2))
