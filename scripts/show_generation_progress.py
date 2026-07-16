"""Apresenta o progresso persistido sem instanciar providers."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scheduling.queue import GenerationQueue  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Define os caminhos consultados pelo relatório."""
    parser = argparse.ArgumentParser(description="Mostra o progresso da geração.")
    parser.add_argument("--queue", default="queues/n1_v1/jobs.jsonl")
    parser.add_argument("--raw-dir", default="datasets/raw")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Conta jobs, exemplos e resultados esperados por provider."""
    arguments = build_parser().parse_args(argv)
    try:
        queue_path = Path(arguments.queue)
        if not queue_path.is_file():
            raise FileNotFoundError(f"Queue file does not exist: {queue_path}")
        queue = GenerationQueue(queue_path)
        jobs = queue.load()
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    raw_dir = Path(arguments.raw_dir)
    statuses = queue.summary()
    providers = sorted({job.provider for job in jobs})
    completed = statuses["completed"]
    percentage = 100.0 * completed / len(jobs) if jobs else 0.0
    found = 0
    missing = 0

    print(f"Total jobs: {len(jobs)}")
    print("Status: " + ", ".join(f"{key}={value}" for key, value in statuses.items()))
    print(f"Completion: {percentage:.2f}%")
    for provider in providers:
        selected = [job for job in jobs if job.provider == provider]
        examples = sum(job.examples_requested for job in selected)
        print(f"Provider {provider}: jobs={len(selected)}, examples={examples}")
        next_job = next(
            (job for job in selected if job.status in {"pending", "retry_wait"}),
            None,
        )
        print(f"Next {provider}: {next_job.chunk_id if next_job else '-'}")
        for job in selected:
            expected = raw_dir / provider / f"{job.chunk_id}.result.json"
            if expected.is_file():
                found += 1
            elif job.status == "completed":
                missing += 1
    failed_or_retry = statuses["failed"] + statuses["retry_wait"]
    print(f"Completed results found: {found}")
    print(f"Missing expected results: {missing}")
    print(f"Failed/retry jobs: {failed_or_retry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
