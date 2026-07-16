"""Testes do preview não destrutivo do escalonamento."""

from pathlib import Path

import pytest

from scripts.preview_generation_schedule import main
from src.scheduling.models import GenerationJob, utc_now_iso
from src.scheduling.queue import GenerationQueue
from src.scheduling.scheduler import DEFAULT_PROVIDER_ORDER


LIMITS_PATH = Path("configs/provider_limits.yaml")


def _job(number: int, provider: str) -> GenerationJob:
    """Cria um job de preview atribuído a um provider fixo."""
    chunk = f"{provider}_{number}"
    timestamp = utc_now_iso()
    return GenerationJob(
        job_id=f"job_{chunk}",
        matrix_row_id=number,
        batch_id=f"batch_{number}",
        chunk_id=chunk,
        provider=provider,
        preferred_model="model",
        prompt_version="n1_v1",
        dataset_split_target="train",
        examples_requested=20,
        prompt_file=f"{chunk}.txt",
        metadata_file=f"{chunk}.json",
        status="pending",
        attempt_count=0,
        created_at=timestamp,
        updated_at=timestamp,
        last_error="",
        result_file="",
    )


def _queue(path, rounds: int = 2) -> bytes:
    """Persiste jobs em ordem de rotação e devolve os bytes originais."""
    jobs = [
        _job(number, provider)
        for number in range(1, rounds + 1)
        for provider in DEFAULT_PROVIDER_ORDER
    ]
    GenerationQueue(path).save(jobs)
    return path.read_bytes()


def _run_lines(output: str) -> list[str]:
    """Extrai apenas decisões run do texto do comando."""
    return [line for line in output.splitlines() if " action=run " in line]


def test_preview_rotation_distribution_and_source_unchanged(tmp_path, capsys) -> None:
    """Requisito: rotação não destrutiva. Resultado esperado: volta inicial e fonte intacta."""
    queue_path = tmp_path / "jobs.jsonl"
    original = _queue(queue_path)

    result = main(
        [
            "--queue",
            str(queue_path),
            "--limits",
            str(LIMITS_PATH),
            "--count",
            "11",
            "--show-waits",
        ]
    )

    output = capsys.readouterr().out
    providers = [line.split("provider=")[1].split()[0] for line in _run_lines(output)]
    assert result == 0
    assert providers[:5] == list(DEFAULT_PROVIDER_ORDER)
    assert providers.count("gemini") == 2
    assert all(f"{provider}=" in output for provider in DEFAULT_PROVIDER_ORDER)
    assert queue_path.read_bytes() == original


def test_preview_exposes_waits_and_never_really_sleeps(tmp_path, capsys) -> None:
    """Requisito: waits simulados. Resultado esperado: linha wait e execução imediata."""
    queue_path = tmp_path / "jobs.jsonl"
    _queue(queue_path)

    result = main(
        [
            "--queue",
            str(queue_path),
            "--limits",
            str(LIMITS_PATH),
            "--count",
            "7",
            "--show-waits",
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert " action=wait " in output
    assert "wait_seconds=6.000" in output


@pytest.mark.parametrize("count", ["0", "-1", "abc"])
def test_preview_rejects_invalid_count(count) -> None:
    """Requisito: count positivo. Resultado esperado: argparse rejeita valor inválido."""
    with pytest.raises(SystemExit):
        main(["--count", count])
