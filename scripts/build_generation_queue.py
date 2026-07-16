"""Constrói uma fila JSONL persistente a partir do manifesto de prompts."""

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scheduling.queue import GenerationQueue, build_jobs_from_manifest  # noqa: E402


DEFAULT_MANIFEST = "prompts/generated/n1_v1/manifest.jsonl"
DEFAULT_QUEUE = "queues/n1_v1/jobs.jsonl"


def build_parser() -> argparse.ArgumentParser:
    """Cria os argumentos do construtor local da fila."""
    parser = argparse.ArgumentParser(
        description="Constrói a fila de geração a partir do manifesto.",
    )
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--queue", default=DEFAULT_QUEUE)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Lê o manifesto, persiste jobs e apresenta um resumo."""
    arguments = build_parser().parse_args(argv)
    queue_path = Path(arguments.queue)
    try:
        if queue_path.exists() and not arguments.overwrite:
            raise FileExistsError(f"Queue file already exists: {queue_path}")
        jobs = build_jobs_from_manifest(arguments.manifest)
        GenerationQueue(queue_path).save(jobs)
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    counts = Counter(job.provider for job in jobs)
    print(f"Entradas do manifesto: {len(jobs)}")
    print(f"Jobs criados: {len(jobs)}")
    print(
        "Jobs por provider: "
        + ", ".join(f"{provider}={counts[provider]}" for provider in sorted(counts))
    )
    print(f"Exemplos pedidos: {sum(job.examples_requested for job in jobs)}")
    print(f"Ficheiro da fila: {queue_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
