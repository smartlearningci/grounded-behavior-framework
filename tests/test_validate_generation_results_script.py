"""Testes do comando de validação e dos sidecars."""

import json

from scripts.validate_generation_results import main
from src.scheduling.models import GenerationJob, utc_now_iso
from src.scheduling.queue import GenerationQueue


def _job(number, attempt=1):
    now = utc_now_iso(); chunk = f"chunk_{number}"
    return GenerationJob(
        f"job_{chunk}", number, "batch", chunk, "gemini", "model", "n1_v2", "train",
        2, f"{chunk}.txt", f"{chunk}.json", "completed", attempt, now, now, "", "",
    )


def _raw(path, job, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "job": {"chunk_id": job.chunk_id, "provider": job.provider, "examples_requested": 2},
        "request": {}, "result": {"text": text}, "execution": {},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_validation_sidecars_report_and_raw_immutability(tmp_path, capsys) -> None:
    """Requisito: sidecars e resumo. Resultado esperado: válido/inválido separados e raw intacto."""
    jobs = [_job(1), _job(2)]
    queue = GenerationQueue(tmp_path / "jobs.jsonl"); queue.save(jobs)
    raw = tmp_path / "raw"
    examples = {"examples": [
        {"context": "Lisboa aqui", "question": "q", "answer": "Lisboa"},
        {"context": "Porto aqui", "question": "q", "answer": "Porto"},
    ]}
    _raw(raw / "gemini" / "chunk_1.result.json", jobs[0], json.dumps(examples))
    _raw(raw / "gemini" / "chunk_2.result.json", jobs[1], '{"examples":[')
    before = {path: path.read_bytes() for path in raw.rglob("*.json")}
    report = tmp_path / "report.jsonl"

    result = main([
        "--queue", str(queue.path), "--raw-dir", str(raw),
        "--validated-dir", str(tmp_path / "validated"),
        "--invalid-dir", str(tmp_path / "invalid"), "--report", str(report),
    ])

    assert result == 0
    assert (tmp_path / "validated/gemini/chunk_1.validation.json").is_file()
    assert (tmp_path / "invalid/gemini/chunk_2.validation.json").is_file()
    assert len(report.read_text().splitlines()) == 2
    assert "valid: 1" in capsys.readouterr().out
    assert all(path.read_bytes() == content for path, content in before.items())
    assert all(job.status == "completed" for job in queue.load())


def test_queue_update_respects_retry_limit_and_preserves_raw(tmp_path) -> None:
    """Requisito: update opcional limitado. Resultado esperado: retry_wait ou failed sem apagar raw."""
    jobs = [_job(1, 1), _job(2, 3)]
    queue = GenerationQueue(tmp_path / "jobs.jsonl"); queue.save(jobs)
    raw = tmp_path / "raw"
    for job in jobs:
        path = raw / "gemini" / f"{job.chunk_id}.result.json"
        _raw(path, job, '{"examples":[')
        job.result_file = str(path)
    queue.save(jobs)

    assert main([
        "--queue", str(queue.path), "--raw-dir", str(raw),
        "--validated-dir", str(tmp_path / "validated"),
        "--invalid-dir", str(tmp_path / "invalid"), "--report", str(tmp_path / "report.jsonl"),
        "--update-queue",
    ]) == 0

    restored = queue.load()
    assert restored[0].status == "retry_wait" and restored[0].result_file == ""
    assert restored[1].status == "failed" and restored[1].result_file
    assert len(list(raw.rglob("*.result.json"))) == 2


def test_missing_result_creates_invalid_sidecar(tmp_path, capsys) -> None:
    """Requisito: resultado ausente. Resultado esperado: missing_result no sidecar e resumo."""
    job = _job(1)
    queue = GenerationQueue(tmp_path / "jobs.jsonl"); queue.save([job])

    assert main([
        "--queue", str(queue.path), "--raw-dir", str(tmp_path / "raw"),
        "--validated-dir", str(tmp_path / "validated"),
        "--invalid-dir", str(tmp_path / "invalid"), "--report", str(tmp_path / "report.jsonl"),
    ]) == 0

    sidecar = json.loads((tmp_path / "invalid/gemini/chunk_1.validation.json").read_text())
    assert sidecar["status"] == "missing_result"
    assert "missing_result: 1" in capsys.readouterr().out
