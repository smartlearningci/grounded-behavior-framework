"""Repõe jobs estruturalmente inválidos sem apagar resultados raw."""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scheduling.config import load_provider_limits  # noqa: E402
from src.scheduling.queue import GenerationQueue  # noqa: E402
from src.scheduling.models import utc_now_iso  # noqa: E402
from src.validation.models import VALIDATION_STATUSES, ValidationResult  # noqa: E402


def positive_integer(value: str) -> int:
    """Valida um limite positivo."""
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Define seleção e confirmação para reset seguro."""
    parser = argparse.ArgumentParser(description="Repõe jobs inválidos para retry.")
    parser.add_argument("--queue", default="queues/n1_v2/jobs.jsonl")
    parser.add_argument("--validation-report", default="reports/n1_v2/validation_report.jsonl")
    parser.add_argument("--raw-dir", default="datasets/raw/n1_v2")
    parser.add_argument("--limits", default="configs/provider_limits.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--status", choices=VALIDATION_STATUSES)
    parser.add_argument("--provider")
    parser.add_argument("--limit", type=positive_integer)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Planeia ou aplica transições, criando um relatório de auditoria."""
    arguments = build_parser().parse_args(argv)
    if not arguments.dry_run and not arguments.yes:
        print("Erro: --yes é obrigatório para modificar a fila.", file=sys.stderr)
        return 2
    try:
        queue = GenerationQueue(arguments.queue)
        if not queue.path.is_file():
            raise FileNotFoundError(f"Queue file does not exist: {queue.path}")
        jobs = queue.load()
        report_path = Path(arguments.validation_report)
        if not report_path.is_file():
            raise FileNotFoundError(f"Validation report does not exist: {report_path}")
        validations = [
            ValidationResult.from_dict(json.loads(line))
            for line in report_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        selected = [result for result in validations if not result.valid]
        if arguments.status:
            selected = [result for result in selected if result.status == arguments.status]
        if arguments.provider:
            selected = [result for result in selected if result.provider == arguments.provider]
        if arguments.limit:
            selected = selected[: arguments.limit]
        by_chunk = {result.chunk_id: result for result in selected}
        limits = load_provider_limits(arguments.limits)
        audit = []
        for job in jobs:
            validation = by_chunk.get(job.chunk_id)
            if validation is None or job.status != "completed":
                continue
            previous = job.result_file or validation.result_file
            target = "retry_wait" if job.attempt_count < limits[job.provider].max_job_attempts else "failed"
            audit.append(
                {
                    "job_id": job.job_id,
                    "chunk_id": job.chunk_id,
                    "provider": job.provider,
                    "validation_status": validation.status,
                    "previous_result_file": previous,
                    "attempt_history_result": validation.result_file,
                    "old_status": job.status,
                    "new_status": target,
                }
            )
            print(f"{job.provider} {job.chunk_id}: completed -> {target}; raw preserved: {previous}")
            if not arguments.dry_run:
                job.status = target
                job.last_error = f"Structural validation failed: {validation.status}"
                if target == "retry_wait":
                    job.result_file = ""
                job.updated_at = utc_now_iso()
        if not arguments.dry_run:
            queue.save(jobs)
            audit_path = report_path.with_name(report_path.stem + ".reset-audit.json")
            _atomic_json(
                audit_path,
                {
                    "reset_timestamp": datetime.now(timezone.utc).isoformat(),
                    "queue": str(queue.path),
                    "raw_directory": str(Path(arguments.raw_dir)),
                    "changes": audit,
                },
            )
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(f"Changes: {len(audit)}")
    return 0


def _atomic_json(path: Path, payload: object) -> None:
    """Publica a auditoria por substituição atómica."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            temporary = Path(file.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
