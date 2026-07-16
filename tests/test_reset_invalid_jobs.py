"""Testes do reset auditável de jobs inválidos."""

import json

from scripts.reset_invalid_jobs import main
from src.scheduling.models import GenerationJob, utc_now_iso
from src.scheduling.queue import GenerationQueue
from src.validation.models import ValidationResult


def _job(number, attempt, raw_path):
    now = utc_now_iso(); chunk = f"chunk_{number}"
    return GenerationJob(
        f"job_{chunk}", number, "batch", chunk, "gemini", "model", "n1_v2", "train",
        2, f"{chunk}.txt", f"{chunk}.json", "completed", attempt, now, now, "", str(raw_path),
    )


def test_reset_dry_run_and_real_preserve_raw_provider_and_attempts(tmp_path) -> None:
    """Requisito: reset seguro. Resultado esperado: dry-run imutável e aplicação preserva raw/atribuição."""
    raw = tmp_path / "raw/gemini/chunk_1.result.json"
    raw.parent.mkdir(parents=True); raw.write_text("raw", encoding="utf-8")
    job = _job(1, 1, raw)
    queue = GenerationQueue(tmp_path / "jobs.jsonl"); queue.save([job])
    validation = ValidationResult(
        job.chunk_id, job.provider, str(raw), False, "invalid_json", 2, 0,
        ["bad"], ["likely_truncation"], "", utc_now_iso(),
    )
    report = tmp_path / "validation.jsonl"
    report.write_text(json.dumps(validation.to_dict()) + "\n", encoding="utf-8")
    original = queue.path.read_bytes()
    args = ["--queue", str(queue.path), "--validation-report", str(report), "--raw-dir", str(tmp_path / "raw")]

    assert main(args + ["--dry-run"]) == 0
    assert queue.path.read_bytes() == original
    assert main(args + ["--yes"]) == 0

    restored = queue.load()[0]
    assert restored.status == "retry_wait" and restored.result_file == ""
    assert restored.provider == "gemini" and restored.attempt_count == 1
    assert raw.read_text() == "raw"
    audit = json.loads((tmp_path / "validation.reset-audit.json").read_text())
    assert audit["changes"][0]["previous_result_file"] == str(raw)


def test_reset_exhausted_job_becomes_failed(tmp_path) -> None:
    """Requisito: limite de tentativas. Resultado esperado: tentativa três termina em failed."""
    raw = tmp_path / "raw/gemini/chunk_2.result.json"
    raw.parent.mkdir(parents=True); raw.write_text("raw", encoding="utf-8")
    job = _job(2, 3, raw)
    queue = GenerationQueue(tmp_path / "jobs.jsonl"); queue.save([job])
    validation = ValidationResult(
        job.chunk_id, job.provider, str(raw), False, "wrong_example_count", 2, 1,
        ["count"], [], "", utc_now_iso(),
    )
    report = tmp_path / "validation.jsonl"
    report.write_text(json.dumps(validation.to_dict()) + "\n", encoding="utf-8")

    assert main([
        "--queue", str(queue.path), "--validation-report", str(report),
        "--raw-dir", str(tmp_path / "raw"), "--yes",
    ]) == 0
    assert queue.load()[0].status == "failed"
    assert raw.exists()
