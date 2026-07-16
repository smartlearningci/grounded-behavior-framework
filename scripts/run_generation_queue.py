"""Executa ou pré-visualiza uma fila persistente de geração."""

import argparse
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution.config import (  # noqa: E402
    RUNTIME_PROVIDERS,
    load_generation_runtime_config,
)
from src.execution.executor import GenerationExecutor  # noqa: E402
from src.execution.result_writer import ResultWriter  # noqa: E402
from src.scheduling.config import load_provider_limits  # noqa: E402
from src.scheduling.queue import GenerationQueue  # noqa: E402
from src.scheduling.rate_limiter import ProviderRateLimiter  # noqa: E402
from src.scheduling.scheduler import RoundRobinScheduler  # noqa: E402


DEFAULT_QUEUE = "queues/n1_v1/jobs.jsonl"
DEFAULT_LIMITS = "configs/provider_limits.yaml"
DEFAULT_RUNTIME = "configs/generation_runtime.yaml"
DEFAULT_PROMPTS = "prompts/generated/n1_v1"
DEFAULT_LIMITER_STATE = "runtime/n1_v1/rate_limiter_state.json"
ENVIRONMENT_VARIABLES = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
}


def positive_integer(value: str) -> int:
    """Valida um inteiro estritamente positivo."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Define a interface segura do executor."""
    parser = argparse.ArgumentParser(description="Executa a fila de geração.")
    parser.add_argument("--queue", default=DEFAULT_QUEUE)
    parser.add_argument("--limits", default=DEFAULT_LIMITS)
    parser.add_argument("--runtime-config", default=DEFAULT_RUNTIME)
    parser.add_argument("--prompt-dir", default=DEFAULT_PROMPTS)
    parser.add_argument("--limiter-state", default=DEFAULT_LIMITER_STATE)
    parser.add_argument("--max-jobs", type=positive_integer, default=5)
    parser.add_argument("--provider", choices=RUNTIME_PROVIDERS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite-results", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--yes", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Valida a execução, constrói dependências e apresenta o resumo."""
    arguments = build_parser().parse_args(argv)
    if arguments.max_jobs > 25 and not arguments.yes:
        print("Erro: valores acima de 25 exigem --yes.", file=sys.stderr)
        return 2
    try:
        queue_path = Path(arguments.queue)
        if not queue_path.is_file():
            raise FileNotFoundError(f"Queue file does not exist: {queue_path}")
        prompt_dir = Path(arguments.prompt_dir)
        if not prompt_dir.is_dir():
            raise FileNotFoundError(f"Prompt directory does not exist: {prompt_dir}")
        limits = load_provider_limits(arguments.limits)
        runtime = load_generation_runtime_config(arguments.runtime_config)
        if arguments.provider:
            limits = {
                name: replace(config, enabled=config.enabled and name == arguments.provider)
                for name, config in limits.items()
            }
        queue = GenerationQueue(queue_path)
        limiter = ProviderRateLimiter(limits)
        scheduler = RoundRobinScheduler(queue, limits, limiter)
        executor = GenerationExecutor(
            queue=queue,
            scheduler=scheduler,
            provider_configs=limits,
            runtime_configs=runtime,
            result_writer=ResultWriter(runtime),
            prompt_base_dir=prompt_dir,
            limiter_state_path=arguments.limiter_state,
            time_source=time.monotonic,
            sleep_function=_forbidden_sleep if arguments.dry_run else time.sleep,
        )

        print("Aviso: quotas e free tiers dos providers podem mudar.")
        print(f"Configuração runtime: {arguments.runtime_config}")
        for name, config in runtime.items():
            if limits[name].enabled:
                print(
                    f"- {name}: temperature={config.temperature}, "
                    f"max_tokens={config.max_tokens}, require_json={config.require_json}"
                )
        if not arguments.dry_run:
            missing = [
                variable
                for provider, variable in ENVIRONMENT_VARIABLES.items()
                if limits[provider].enabled and not os.getenv(variable)
            ]
            print("Variáveis em falta: " + (", ".join(missing) if missing else "nenhuma"))

        summary = executor.run(
            max_jobs=arguments.max_jobs,
            dry_run=arguments.dry_run,
            overwrite_results=arguments.overwrite_results,
            stop_on_error=arguments.stop_on_error,
        )
    except KeyboardInterrupt:
        print("Execução interrompida; a fila pode ser retomada.", file=sys.stderr)
        return 130
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    for index, record in enumerate(executor.last_records, start=1):
        destination = f" -> {record.result_file}" if record.result_file else ""
        print(
            f"[{index}/{arguments.max_jobs}] {record.provider} "
            f"{record.chunk_id} {record.status}{destination}"
        )
    print(f"Completed: {summary.jobs_completed}")
    print(f"Retry wait: {summary.jobs_retry_wait}")
    print(f"Failed: {summary.jobs_failed}")
    print(f"Skipped existing: {summary.jobs_skipped_existing}")
    print(
        "Provider distribution: "
        + ", ".join(f"{key}={value}" for key, value in summary.providers_used.items())
    )
    print(f"Examples requested: {summary.examples_requested}")
    print(f"Duration: {summary.duration_seconds:.3f}s")
    print(
        "Queue summary: "
        + ", ".join(f"{key}={value}" for key, value in queue.summary().items())
    )
    return 0


def _forbidden_sleep(seconds: float) -> None:
    """Garante que dry-run nunca realiza uma espera real."""
    raise RuntimeError(f"Dry-run attempted to sleep for {seconds} seconds")


if __name__ == "__main__":
    raise SystemExit(main())
