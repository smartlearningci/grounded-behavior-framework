"""Testes da interface de linha de comandos do executor."""

from unittest.mock import patch

import pytest

from scripts.run_generation_queue import build_parser, main
from src.scheduling.models import GenerationJob, utc_now_iso
from src.scheduling.queue import GenerationQueue
from src.scheduling.scheduler import DEFAULT_PROVIDER_ORDER


def _prepare(tmp_path):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    jobs = []
    now = utc_now_iso()
    for number, provider in enumerate(DEFAULT_PROVIDER_ORDER, start=1):
        chunk = f"B0001_C{number:02d}"
        job = GenerationJob(
            f"job_{chunk}", number, "B0001", chunk, provider, "provider-selected",
            "n1_v1", "train", 20, f"{chunk}.prompt.txt", f"{chunk}.json",
            "pending", 0, now, now, "", "",
        )
        jobs.append(job)
        (prompts / job.prompt_file).write_text("prompt", encoding="utf-8")
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    queue.save(jobs)
    return queue, prompts


def _args(queue, prompts):
    return [
        "--queue", str(queue.path), "--limits", "configs/provider_limits.yaml",
        "--runtime-config", "configs/generation_runtime.yaml",
        "--prompt-dir", str(prompts), "--limiter-state", str(queue.path.parent / "state.json"),
    ]


def test_default_max_jobs_is_five() -> None:
    """Requisito: limite seguro por omissão. Resultado esperado: max_jobs igual a cinco."""
    assert build_parser().parse_args([]).max_jobs == 5


def test_more_than_twenty_five_requires_yes(tmp_path, capsys) -> None:
    """Requisito: confirmação acima de 25. Resultado esperado: código 2 sem --yes."""
    queue, prompts = _prepare(tmp_path)

    assert main(_args(queue, prompts) + ["--max-jobs", "26", "--dry-run"]) == 2
    assert "--yes" in capsys.readouterr().err


def test_dry_run_prints_rotation_and_does_not_mutate(tmp_path, capsys) -> None:
    """Requisito: dry-run CLI. Resultado esperado: cinco providers sem alterar a fila."""
    queue, prompts = _prepare(tmp_path)
    original = queue.path.read_bytes()

    result = main(_args(queue, prompts) + ["--dry-run"])
    output = capsys.readouterr().out

    assert result == 0
    positions = [output.index(f" {provider} B0001") for provider in DEFAULT_PROVIDER_ORDER]
    assert positions == sorted(positions)
    assert queue.path.read_bytes() == original
    assert "Completed: 0" in output and "Provider distribution:" in output


def test_invalid_provider_and_missing_queue_are_rejected(tmp_path, capsys) -> None:
    """Requisito: argumentos e ficheiros válidos. Resultado esperado: argparse ou erro claro."""
    with pytest.raises(SystemExit):
        main(["--provider", "unknown"])
    result = main(["--queue", str(tmp_path / "missing.jsonl"), "--dry-run"])
    assert result == 1 and "does not exist" in capsys.readouterr().err


def test_keyboard_interrupt_returns_130(tmp_path, capsys) -> None:
    """Requisito: interrupção CLI. Resultado esperado: código 130 e mensagem retomável."""
    queue, prompts = _prepare(tmp_path)
    with patch("scripts.run_generation_queue.GenerationExecutor.run", side_effect=KeyboardInterrupt):
        result = main(_args(queue, prompts) + ["--dry-run"])
    assert result == 130
    assert "retomada" in capsys.readouterr().err
