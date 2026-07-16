"""Testes do relatório local de progresso."""

from scripts.show_generation_progress import main
from src.scheduling.models import GenerationJob, utc_now_iso
from src.scheduling.queue import GenerationQueue


def _job(number, provider, status):
    now = utc_now_iso()
    chunk = f"{provider}_{number}"
    return GenerationJob(
        f"job_{chunk}", number, "batch", chunk, provider, "model", "n1_v1", "train",
        20, f"{chunk}.txt", f"{chunk}.json", status, 0, now, now, "", "",
    )


def test_progress_reports_status_provider_results_and_next_job(tmp_path, capsys) -> None:
    """Requisito: progresso completo. Resultado esperado: contagens, ficheiros e próximo job."""
    jobs = [
        _job(1, "gemini", "completed"), _job(2, "gemini", "pending"),
        _job(1, "groq", "retry_wait"), _job(1, "mistral", "failed"),
    ]
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    queue.save(jobs)
    raw = tmp_path / "raw"
    result = raw / "gemini" / "gemini_1.result.json"
    result.parent.mkdir(parents=True)
    result.write_text("{}", encoding="utf-8")

    assert main(["--queue", str(queue.path), "--raw-dir", str(raw)]) == 0
    output = capsys.readouterr().out
    assert "Total jobs: 4" in output
    assert "completed=1" in output and "pending=1" in output
    assert "Completion: 25.00%" in output
    assert "Provider gemini: jobs=2, examples=40" in output
    assert "Completed results found: 1" in output
    assert "Missing expected results: 0" in output
    assert "Failed/retry jobs: 2" in output
    assert "Next gemini: gemini_2" in output


def test_progress_detects_missing_completed_result(tmp_path, capsys) -> None:
    """Requisito: resultados esperados. Resultado esperado: completed sem ficheiro é contado."""
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    queue.save([_job(1, "gemini", "completed")])

    assert main(["--queue", str(queue.path), "--raw-dir", str(tmp_path / "raw")]) == 0
    assert "Missing expected results: 1" in capsys.readouterr().out


def test_progress_rejects_missing_queue(tmp_path, capsys) -> None:
    """Requisito: fila existente. Resultado esperado: código 1 com mensagem clara."""
    assert main(["--queue", str(tmp_path / "missing.jsonl")]) == 1
    assert "does not exist" in capsys.readouterr().err
