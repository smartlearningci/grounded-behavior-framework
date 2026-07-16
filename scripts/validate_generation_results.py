"""Valida resultados raw e escreve sidecars sem alterar os originais."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scheduling.config import load_provider_limits  # noqa: E402
from src.scheduling.models import VALID_JOB_STATUSES  # noqa: E402
from src.scheduling.models import utc_now_iso  # noqa: E402
from src.scheduling.queue import GenerationQueue  # noqa: E402
from src.validation.reporting import (  # noqa: E402
    validation_summary,
    write_validation_report,
    write_validation_sidecar,
)
from src.validation.result_validator import missing_result, validate_result_file  # noqa: E402


def positive_integer(value: str) -> int:
    """Valida limites estritamente positivos."""
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Define os caminhos v2 recomendados e filtros opcionais."""
    parser = argparse.ArgumentParser(description="Valida resultados de geração.")
    parser.add_argument("--queue", default="queues/n1_v2/jobs.jsonl")
    parser.add_argument("--raw-dir", default="datasets/raw/n1_v2")
    parser.add_argument("--validated-dir", default="datasets/validated/n1_v2")
    parser.add_argument("--invalid-dir", default="datasets/invalid/n1_v2")
    parser.add_argument("--report", default="reports/n1_v2/validation_report.jsonl")
    parser.add_argument("--limits", default="configs/provider_limits.yaml")
    parser.add_argument("--provider")
    parser.add_argument("--status", choices=VALID_JOB_STATUSES, default="completed")
    parser.add_argument("--limit", type=positive_integer)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--update-queue", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Valida jobs selecionados e opcionalmente agenda retries limitados."""
    arguments = build_parser().parse_args(argv)
    try:
        queue = GenerationQueue(arguments.queue)
        if not queue.path.is_file():
            raise FileNotFoundError(f"Queue file does not exist: {queue.path}")
        jobs = [job for job in queue.load() if job.status == arguments.status]
        if arguments.provider:
            jobs = [job for job in jobs if job.provider == arguments.provider]
        if arguments.limit:
            jobs = jobs[: arguments.limit]
        limits = load_provider_limits(arguments.limits) if arguments.update_queue else {}
        raw_dir = Path(arguments.raw_dir)
        results = []
        for job in jobs:
            configured = Path(job.result_file) if job.result_file else None
            fallback = raw_dir / job.provider / f"{job.chunk_id}.result.json"
            result_path = configured if configured is not None and configured.is_file() else fallback
            if result_path.is_file():
                validation = validate_result_file(result_path)
                if not validation.chunk_id:
                    validation.chunk_id = job.chunk_id
                if not validation.provider:
                    validation.provider = job.provider
            else:
                validation = missing_result(
                    job.chunk_id, job.provider, result_path, job.examples_requested
                )
            sidecar_root = Path(arguments.validated_dir if validation.valid else arguments.invalid_dir)
            sidecar = sidecar_root / job.provider / f"{job.chunk_id}.validation.json"
            write_validation_sidecar(validation, sidecar, arguments.overwrite)
            results.append(validation)
            if arguments.update_queue and not validation.valid and job.status == "completed":
                if job.attempt_count < limits[job.provider].max_job_attempts:
                    job.status = "retry_wait"
                    job.last_error = f"Structural validation failed: {validation.status}"
                    job.result_file = ""
                else:
                    job.status = "failed"
                    job.last_error = f"Structural validation failed: {validation.status}"
                job.updated_at = utc_now_iso()
        write_validation_report(results, arguments.report, arguments.overwrite)
        if arguments.update_queue:
            queue.save(queue.load() if not jobs else _merge_jobs(queue.load(), jobs))
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    summary = validation_summary(results)
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


def _merge_jobs(all_jobs, changed_jobs):
    """Substitui jobs alterados por ID preservando a ordem completa da fila."""
    changed = {job.job_id: job for job in changed_jobs}
    return [changed.get(job.job_id, job) for job in all_jobs]


if __name__ == "__main__":
    raise SystemExit(main())
