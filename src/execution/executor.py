"""Executa a fila de geração de forma retomável e determinística."""

import json
import os
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

from src.core.factory import create_component
from src.core.interfaces import AIProvider, GenerationRequest
from src.scheduling.config import ProviderLimitConfig
from src.scheduling.models import GenerationJob
from src.scheduling.queue import GenerationQueue
from src.scheduling.scheduler import RoundRobinScheduler

from .config import ProviderRuntimeConfig
from .errors import (
    PromptFileError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderTemporaryError,
    ResultFileError,
    classify_provider_exception,
    sanitize_error,
)
from .result_writer import ResultWriter, validate_existing_result


PLACEHOLDER_MODELS = {"", "free-model-fallback", "provider-selected"}


@dataclass
class ExecutionSummary:
    """Resume uma passagem do executor pela fila."""

    jobs_requested: int
    jobs_started: int = 0
    jobs_completed: int = 0
    jobs_retry_wait: int = 0
    jobs_failed: int = 0
    jobs_skipped_existing: int = 0
    providers_used: dict[str, int] = field(default_factory=dict)
    examples_requested: int = 0
    duration_seconds: float = 0.0
    stopped_reason: str = ""


@dataclass
class ExecutionRecord:
    """Descreve o resultado observável de um único job."""

    job_id: str
    chunk_id: str
    provider: str
    status: str
    result_file: str
    error: str
    duration_seconds: float


class GenerationExecutor:
    """Coordena fila, scheduler, providers e persistência imediata."""

    def __init__(
        self,
        queue: GenerationQueue,
        scheduler: RoundRobinScheduler,
        provider_configs: dict[str, ProviderLimitConfig],
        runtime_configs: dict[str, ProviderRuntimeConfig],
        result_writer: ResultWriter,
        prompt_base_dir: str | Path,
        limiter_state_path: str | Path,
        time_source: Callable[[], float] = time.monotonic,
        sleep_function: Callable[[float], None] = time.sleep,
        provider_factory: Callable[[str], AIProvider] | None = None,
    ) -> None:
        """Recebe todas as dependências mutáveis para permitir mocks."""
        self.queue = queue
        self.scheduler = scheduler
        self.provider_configs = provider_configs
        self.runtime_configs = runtime_configs
        self.result_writer = result_writer
        self.prompt_base_dir = Path(prompt_base_dir)
        self.limiter_state_path = Path(limiter_state_path)
        self.time_source = time_source
        self.sleep_function = sleep_function
        self.provider_factory = provider_factory or _default_provider_factory
        self.provider_instances: dict[str, AIProvider] = {}
        self.consecutive_failures: Counter[str] = Counter()
        self.last_records: list[ExecutionRecord] = []

    def run(
        self,
        max_jobs: int,
        dry_run: bool = False,
        overwrite_results: bool = False,
        stop_on_error: bool = False,
    ) -> ExecutionSummary:
        """Consome até max_jobs, esperando apenas no modo real."""
        if isinstance(max_jobs, bool) or not isinstance(max_jobs, int) or max_jobs <= 0:
            raise ValueError("max_jobs must be a positive integer")
        started = self.time_source()
        summary = ExecutionSummary(jobs_requested=max_jobs)
        distribution: Counter[str] = Counter()
        self.last_records = []
        self.restore_limiter_state()
        if not dry_run:
            self.queue.reset_running_jobs()

        try:
            while len(self.last_records) < max_jobs:
                decision = self.scheduler.next_decision()
                if decision.action == "empty":
                    summary.stopped_reason = "queue_empty"
                    break
                if decision.action == "wait":
                    if dry_run:
                        summary.stopped_reason = "dry_run_wait"
                        break
                    if not isfinite(decision.wait_seconds):
                        summary.stopped_reason = "no_finite_wait"
                        break
                    self.save_limiter_state()
                    print(
                        f"Waiting {decision.wait_seconds:.1f} seconds; "
                        "all pending providers are cooling down."
                    )
                    self.sleep_function(decision.wait_seconds)
                    continue

                job = decision.job
                assert job is not None
                summary.examples_requested += job.examples_requested
                if dry_run:
                    record = ExecutionRecord(
                        job_id=job.job_id,
                        chunk_id=job.chunk_id,
                        provider=job.provider,
                        status="dry_run",
                        result_file="",
                        error="",
                        duration_seconds=0.0,
                    )
                else:
                    record = self.run_one(job, overwrite_results)
                    summary.jobs_started += 1
                self.last_records.append(record)
                distribution[job.provider] += 1
                if record.status == "completed":
                    summary.jobs_completed += 1
                elif record.status == "retry_wait":
                    summary.jobs_retry_wait += 1
                elif record.status == "failed":
                    summary.jobs_failed += 1
                elif record.status == "skipped_existing":
                    summary.jobs_completed += 1
                    summary.jobs_skipped_existing += 1
                if stop_on_error and record.error:
                    summary.stopped_reason = "stop_on_error"
                    break
            else:
                summary.stopped_reason = "max_jobs_reached"
        except KeyboardInterrupt:
            if not dry_run:
                self.queue.reset_running_jobs()
                self.save_limiter_state()
            summary.stopped_reason = "interrupted"
            raise
        finally:
            summary.providers_used = dict(distribution)
            summary.duration_seconds = max(0.0, self.time_source() - started)
        return summary

    def run_one(
        self,
        job: GenerationJob,
        overwrite_results: bool = False,
    ) -> ExecutionRecord:
        """Executa e persiste um job, normalizando qualquer falha do provider."""
        started_clock = self.time_source()
        started_at = _utc_now()
        self.scheduler.mark_running(job)
        existing = self.result_writer.success_path(job)
        try:
            self.save_limiter_state()
            if existing.exists() and not overwrite_results:
                validate_existing_result(existing)
                self.scheduler.mark_completed(job, str(existing))
                self.consecutive_failures[job.provider] = 0
                return self._record(job, "skipped_existing", str(existing), "", started_clock)

            prompt_text = self._read_prompt(job)
            request = self._build_request(job, prompt_text)
            provider = self._provider(job.provider)
            result = provider.generate(request)
            completed_at = _utc_now()
            result_path = self.result_writer.write_success(
                job,
                request,
                result,
                prompt_text,
                started_at,
                completed_at,
                overwrite=overwrite_results,
            )
            self.scheduler.mark_completed(job, str(result_path))
            self.consecutive_failures[job.provider] = 0
            self.save_limiter_state()
            return self._record(job, "completed", str(result_path), "", started_clock)
        except KeyboardInterrupt:
            raise
        except Exception as raw_error:
            error = self._normalise_error(raw_error)
            completed_at = _utc_now()
            try:
                self.result_writer.write_failure_record(
                    job, job.provider, error, started_at, completed_at
                )
            except Exception as writer_error:
                error = ResultFileError(
                    f"{sanitize_error(error)}; failure record: {sanitize_error(writer_error)}"
                )
            self._apply_failure(job, error)
            self.save_limiter_state()
            return self._record(
                job, job.status, "", sanitize_error(error), started_clock
            )

    def save_limiter_state(self) -> None:
        """Persiste o estado num JSON atómico sem informação sensível."""
        self.limiter_state_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(
            self.scheduler.rate_limiter.export_state(),
            ensure_ascii=False,
            indent=2,
        ) + "\n"
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.limiter_state_path.parent,
                prefix=f".{self.limiter_state_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                file.write(content)
                temporary = Path(file.name)
            os.replace(temporary, self.limiter_state_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def restore_limiter_state(self) -> None:
        """Restaura estado quando existe e rejeita JSON malformado claramente."""
        if not self.limiter_state_path.exists():
            return
        try:
            state = json.loads(self.limiter_state_path.read_text(encoding="utf-8"))
            self.scheduler.rate_limiter.restore_state(state)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                f"Malformed limiter state file: {self.limiter_state_path}: {exc}"
            ) from exc

    def _read_prompt(self, job: GenerationJob) -> str:
        """Resolve um nome relativo sem permitir fuga do diretório base."""
        relative = Path(job.prompt_file)
        base = self.prompt_base_dir.resolve()
        path = (base / relative).resolve()
        if relative.is_absolute() or path != base and base not in path.parents:
            raise PromptFileError(f"Prompt path leaves prompt directory: {job.prompt_file}")
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise PromptFileError(f"Could not read prompt: {job.prompt_file}") from exc

    def _build_request(self, job: GenerationJob, prompt_text: str) -> GenerationRequest:
        """Combina o job com a configuração validada do notebook."""
        config = self.runtime_configs[job.provider]
        preferred = job.preferred_model.strip()
        model = None if preferred.lower() in PLACEHOLDER_MODELS else preferred
        return GenerationRequest(
            prompt=prompt_text,
            system_prompt=config.system_prompt,
            model=model,
            model_candidates=[],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            require_json=config.require_json,
        )

    def _provider(self, provider_name: str) -> AIProvider:
        """Cria apenas o provider selecionado e reutiliza-o nesta execução."""
        if provider_name not in self.provider_instances:
            self.provider_instances[provider_name] = self.provider_factory(provider_name)
        return self.provider_instances[provider_name]

    def _normalise_error(self, error: Exception) -> Exception:
        """Preserva erros internos e classifica exceções de adapters."""
        if isinstance(error, (PromptFileError, ResultFileError)):
            return error
        return classify_provider_exception(error)

    def _apply_failure(self, job: GenerationJob, error: Exception) -> None:
        """Atualiza cooldown, estado do job e eventual pausa do provider."""
        if isinstance(error, ProviderRateLimitError):
            self.scheduler.rate_limiter.record_rate_limit(
                job.provider, error.retry_after_seconds
            )
        temporary = isinstance(error, (ProviderRateLimitError, ProviderTemporaryError))
        if temporary and job.attempt_count < self.provider_configs[job.provider].max_job_attempts:
            self.scheduler.mark_retry_wait(job, sanitize_error(error))
        else:
            self.scheduler.mark_failed(job, sanitize_error(error))

        self.consecutive_failures[job.provider] += 1
        threshold = self.runtime_configs[job.provider].stop_provider_after_consecutive_failures
        if isinstance(error, ProviderAuthenticationError) or self.consecutive_failures[job.provider] >= threshold:
            self.scheduler.pause_provider(job.provider)

    def _record(
        self,
        job: GenerationJob,
        status: str,
        result_file: str,
        error: str,
        started: float,
    ) -> ExecutionRecord:
        """Cria um registo com duração monotónica não negativa."""
        return ExecutionRecord(
            job_id=job.job_id,
            chunk_id=job.chunk_id,
            provider=job.provider,
            status=status,
            result_file=result_file,
            error=error,
            duration_seconds=max(0.0, self.time_source() - started),
        )


def _default_provider_factory(provider_name: str) -> AIProvider:
    """Adapta a factory estável ao nome selecionado pelo scheduler."""
    return create_component("generation_executor", {"provider": provider_name})


def _utc_now() -> str:
    """Devolve timestamp UTC ISO 8601 para os artefactos."""
    return datetime.now(timezone.utc).isoformat()
