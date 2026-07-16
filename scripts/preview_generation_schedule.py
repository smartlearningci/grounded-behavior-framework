"""Pré-visualiza decisões round-robin sem alterar a fila nem executar APIs."""

import argparse
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scheduling.config import load_provider_limits  # noqa: E402
from src.scheduling.queue import GenerationQueue  # noqa: E402
from src.scheduling.rate_limiter import ProviderRateLimiter  # noqa: E402
from src.scheduling.scheduler import RoundRobinScheduler  # noqa: E402


DEFAULT_QUEUE = "queues/n1_v1/jobs.jsonl"
DEFAULT_LIMITS = "configs/provider_limits.yaml"


class PreviewClock:
    """Relógio monotónico e UTC incrementável usado apenas no preview."""

    def __init__(self) -> None:
        """Inicia ambos os relógios num ponto determinístico."""
        self.monotonic_value = 0.0
        self.utc_value = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def monotonic(self) -> float:
        """Devolve o instante monotónico atual."""
        return self.monotonic_value

    def utc_now(self) -> datetime:
        """Devolve o instante civil UTC atual."""
        return self.utc_value

    def advance(self, seconds: float) -> None:
        """Avança os dois relógios pelo mesmo número de segundos."""
        self.monotonic_value += seconds
        self.utc_value += timedelta(seconds=seconds)


def positive_integer(value: str) -> int:
    """Valida o número estritamente positivo de decisões."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Cria os argumentos da pré-visualização não destrutiva."""
    parser = argparse.ArgumentParser(
        description="Pré-visualiza o escalonamento sem executar providers.",
    )
    parser.add_argument("--queue", default=DEFAULT_QUEUE)
    parser.add_argument("--limits", default=DEFAULT_LIMITS)
    parser.add_argument("--count", type=positive_integer, default=25)
    parser.add_argument("--show-waits", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Copia a fila e simula decisões com um relógio incrementável."""
    arguments = build_parser().parse_args(argv)
    source_queue = Path(arguments.queue)
    try:
        if not source_queue.is_file():
            raise FileNotFoundError(f"Queue file does not exist: {source_queue}")
        configs = load_provider_limits(arguments.limits)
        with tempfile.TemporaryDirectory(prefix="grounded-schedule-preview-") as folder:
            preview_path = Path(folder) / "jobs.jsonl"
            shutil.copyfile(source_queue, preview_path)
            queue = GenerationQueue(preview_path)
            clock = PreviewClock()
            limiter = ProviderRateLimiter(
                configs,
                time_source=clock.monotonic,
                sleep_function=_forbidden_sleep,
                utc_now_source=clock.utc_now,
            )
            scheduler = RoundRobinScheduler(queue, configs, limiter)
            distribution: Counter[str] = Counter()

            for sequence in range(1, arguments.count + 1):
                decision = scheduler.next_decision()
                if decision.action == "run":
                    job = decision.job
                    assert job is not None
                    print(
                        _format_decision(
                            sequence,
                            decision.action,
                            job.provider,
                            job.chunk_id,
                            decision.wait_seconds,
                            decision.reason,
                        )
                    )
                    scheduler.mark_running(job)
                    scheduler.mark_completed(
                        job,
                        result_file=f"preview/{job.chunk_id}.json",
                    )
                    distribution[job.provider] += 1
                    continue
                if decision.action == "wait":
                    if arguments.show_waits:
                        print(
                            _format_decision(
                                sequence,
                                decision.action,
                                None,
                                None,
                                decision.wait_seconds,
                                decision.reason,
                            )
                        )
                    if not isfinite(decision.wait_seconds):
                        break
                    clock.advance(decision.wait_seconds)
                    continue
                print(
                    _format_decision(
                        sequence,
                        decision.action,
                        None,
                        None,
                        0.0,
                        decision.reason,
                    )
                )
                break

            print(
                "Distribuição por provider: "
                + ", ".join(
                    f"{provider}={distribution[provider]}"
                    for provider in scheduler.provider_order
                    if distribution[provider]
                )
            )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


def _format_decision(
    sequence: int,
    action: str,
    provider: str | None,
    chunk_id: str | None,
    wait_seconds: float,
    reason: str,
) -> str:
    """Formata uma linha estável e legível da simulação."""
    return (
        f"{sequence:03d} action={action} provider={provider or '-'} "
        f"chunk_id={chunk_id or '-'} wait_seconds={wait_seconds:.3f} "
        f"reason={reason}"
    )


def _forbidden_sleep(seconds: float) -> None:
    """Falha imediatamente se o preview tentar realizar uma espera real."""
    raise RuntimeError(f"Preview attempted a real sleep of {seconds} seconds")


if __name__ == "__main__":
    raise SystemExit(main())
