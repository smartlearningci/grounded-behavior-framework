"""Escalonador round-robin determinístico para jobs já atribuídos."""

import re

from .config import ProviderLimitConfig
from .models import GenerationJob, ScheduleDecision, utc_now_iso
from .queue import GenerationQueue
from .rate_limiter import ProviderRateLimiter


DEFAULT_PROVIDER_ORDER = ("gemini", "groq", "mistral", "openrouter", "cerebras")
RUNNABLE_STATUSES = {"pending", "retry_wait"}
MAX_ERROR_LENGTH = 1000


class RoundRobinScheduler:
    """Roda entre filas por provider sem alterar a atribuição de cada job."""

    def __init__(
        self,
        queue: GenerationQueue,
        provider_configs: dict[str, ProviderLimitConfig],
        rate_limiter: ProviderRateLimiter,
        provider_order: list[str] | tuple[str, ...] = DEFAULT_PROVIDER_ORDER,
    ) -> None:
        """Configura fila, limites e ordem de rotação explícita."""
        if not provider_order:
            raise ValueError("provider_order must not be empty")
        unknown = [provider for provider in provider_order if provider not in provider_configs]
        if unknown:
            raise ValueError("provider_order contains unknown providers: " + ", ".join(unknown))
        if len(provider_order) != len(set(provider_order)):
            raise ValueError("provider_order must not contain duplicates")
        self.queue = queue
        self.provider_configs = provider_configs
        self.rate_limiter = rate_limiter
        self.provider_order = tuple(provider_order)
        self._next_provider_index = 0

    def next_job(self) -> GenerationJob | None:
        """Devolve apenas o job da próxima decisão run, quando existir."""
        decision = self.next_decision()
        return decision.job if decision.action == "run" else None

    def next_decision(self) -> ScheduleDecision:
        """Seleciona por rotação, ou devolve espera mínima/estado vazio."""
        runnable = [
            job for job in self.queue.load() if job.status in RUNNABLE_STATUSES
        ]
        if not runnable:
            return ScheduleDecision(
                job=None,
                action="empty",
                provider=None,
                wait_seconds=0.0,
                reason="No pending or retry_wait jobs",
            )

        jobs_by_provider = {
            provider: [job for job in runnable if job.provider == provider]
            for provider in self.provider_order
        }
        for offset in range(len(self.provider_order)):
            index = (self._next_provider_index + offset) % len(self.provider_order)
            provider = self.provider_order[index]
            if not jobs_by_provider[provider]:
                continue
            config = self.provider_configs[provider]
            if not config.enabled:
                continue
            if self.rate_limiter.can_run(provider):
                self._next_provider_index = (index + 1) % len(self.provider_order)
                job = jobs_by_provider[provider][0]
                return ScheduleDecision(
                    job=job,
                    action="run",
                    provider=provider,
                    wait_seconds=0.0,
                    reason="Provider is next in round-robin order and eligible",
                )

        waits = []
        blocked_providers = []
        for provider in self.provider_order:
            if not jobs_by_provider[provider]:
                continue
            config = self.provider_configs[provider]
            if not config.enabled:
                continue
            wait = self.rate_limiter.seconds_until_available(provider)
            blocked_providers.append(provider)
            if wait > 0:
                waits.append(wait)
        if waits:
            shortest_wait = min(waits)
            return ScheduleDecision(
                job=None,
                action="wait",
                provider=None,
                wait_seconds=shortest_wait,
                reason=(
                    "All enabled providers with queued jobs are temporarily unavailable: "
                    + ", ".join(blocked_providers)
                ),
            )
        return ScheduleDecision(
            job=None,
            action="empty",
            provider=None,
            wait_seconds=0.0,
            reason="Queued jobs belong only to disabled or unscheduled providers",
        )

    def mark_running(self, job: GenerationJob) -> None:
        """Transita um job elegível, incrementa tentativas e regista o pedido."""
        self._require_status(job, RUNNABLE_STATUSES, "running")
        config = self.provider_configs[job.provider]
        if job.attempt_count >= config.max_job_attempts:
            raise ValueError(
                f"Job {job.job_id} reached max_job_attempts for {job.provider}"
            )
        job.status = "running"
        job.attempt_count += 1
        self.rate_limiter.record_request(job.provider)
        self.queue.update_job(job)

    def mark_completed(self, job: GenerationJob, result_file: str) -> None:
        """Conclui um job running e guarda o caminho do resultado."""
        self._require_status(job, {"running"}, "completed")
        if not result_file:
            raise ValueError("result_file must not be empty")
        job.status = "completed"
        job.result_file = result_file
        job.last_error = ""
        self.queue.update_job(job)

    def mark_retry_wait(self, job: GenerationJob, error: str) -> None:
        """Devolve um job running à espera de retry com erro sanitizado."""
        self._require_status(job, {"running"}, "retry_wait")
        job.status = "retry_wait"
        job.last_error = _sanitize_error(error)
        self.queue.update_job(job)

    def mark_failed(self, job: GenerationJob, error: str) -> None:
        """Termina um job running com erro sanitizado e limitado."""
        self._require_status(job, {"running"}, "failed")
        job.status = "failed"
        job.last_error = _sanitize_error(error)
        self.queue.update_job(job)

    def pause_provider(self, provider: str) -> int:
        """Pausa jobs pendentes ou em retry do provider indicado."""
        self._require_provider(provider)
        jobs = self.queue.load()
        timestamp = utc_now_iso()
        changed = 0
        for job in jobs:
            if job.provider == provider and job.status in RUNNABLE_STATUSES:
                job.status = "paused"
                job.updated_at = timestamp
                changed += 1
        if changed:
            self.queue.save(jobs)
        return changed

    def resume_provider(self, provider: str) -> int:
        """Retoma como pending os jobs pausados do provider indicado."""
        self._require_provider(provider)
        jobs = self.queue.load()
        timestamp = utc_now_iso()
        changed = 0
        for job in jobs:
            if job.provider == provider and job.status == "paused":
                job.status = "pending"
                job.updated_at = timestamp
                changed += 1
        if changed:
            self.queue.save(jobs)
        return changed

    @staticmethod
    def _require_status(
        job: GenerationJob,
        allowed: set[str],
        target: str,
    ) -> None:
        """Rejeita transições fora do diagrama de estados definido."""
        if job.status not in allowed:
            raise ValueError(
                f"Invalid job transition {job.status} -> {target} for {job.job_id}"
            )

    def _require_provider(self, provider: str) -> None:
        """Confirma que o provider possui configuração de escalonamento."""
        if provider not in self.provider_configs:
            raise ValueError(f"Unknown scheduled provider: {provider}")


def _sanitize_error(error: str) -> str:
    """Oculta tokens Bearer/Authorization óbvios e limita o texto persistido."""
    text = str(error)
    text = re.sub(
        r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+",
        r"\1[REDACTED]",
        text,
    )
    text = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1[REDACTED]", text)
    return text[:MAX_ERROR_LENGTH]
