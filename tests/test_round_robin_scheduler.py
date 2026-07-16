"""Testes do escalonador round-robin persistente."""

from datetime import datetime, timedelta, timezone

import pytest

from src.scheduling.config import ProviderLimitConfig
from src.scheduling.models import GenerationJob, utc_now_iso
from src.scheduling.queue import GenerationQueue
from src.scheduling.rate_limiter import ProviderRateLimiter
from src.scheduling.scheduler import DEFAULT_PROVIDER_ORDER, RoundRobinScheduler


class FakeClock:
    """Relógio determinístico que nunca dorme."""

    def __init__(self) -> None:
        self.value = 0.0
        self.utc_value = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def monotonic(self) -> float:
        return self.value

    def utc_now(self) -> datetime:
        return self.utc_value

    def advance(self, seconds: float) -> None:
        self.value += seconds
        self.utc_value += timedelta(seconds=seconds)


def _configs(**disabled: bool) -> dict[str, ProviderLimitConfig]:
    return {
        provider: ProviderLimitConfig(
            provider=provider,
            enabled=not disabled.get(provider, False),
            min_delay_seconds=0,
            max_requests_per_minute=None,
            max_requests_per_day=None,
            max_consecutive_requests=1,
            max_job_attempts=3,
            cooldown_after_rate_limit_seconds=60,
        )
        for provider in DEFAULT_PROVIDER_ORDER
    }


def _job(number: int, provider: str, status: str = "pending") -> GenerationJob:
    timestamp = utc_now_iso()
    return GenerationJob(
        job_id=f"job_{provider}_{number}",
        matrix_row_id=number,
        batch_id="batch",
        chunk_id=f"{provider}_{number}",
        provider=provider,
        preferred_model="model",
        prompt_version="n1_v1",
        dataset_split_target="train",
        examples_requested=20,
        prompt_file=f"{provider}_{number}.txt",
        metadata_file=f"{provider}_{number}.json",
        status=status,
        attempt_count=0,
        created_at=timestamp,
        updated_at=timestamp,
        last_error="",
        result_file="",
    )


def _scheduler(tmp_path, jobs, configs=None):
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    queue.save(jobs)
    clock = FakeClock()
    selected_configs = configs or _configs()
    sleeps: list[float] = []
    limiter = ProviderRateLimiter(
        selected_configs,
        time_source=clock.monotonic,
        sleep_function=sleeps.append,
        utc_now_source=clock.utc_now,
    )
    scheduler = RoundRobinScheduler(queue, selected_configs, limiter)
    return scheduler, queue, limiter, clock, sleeps


def _run_and_complete(scheduler: RoundRobinScheduler) -> GenerationJob:
    decision = scheduler.next_decision()
    assert decision.action == "run"
    assert decision.job is not None
    scheduler.mark_running(decision.job)
    scheduler.mark_completed(decision.job, f"results/{decision.job.chunk_id}.json")
    return decision.job


def test_exact_rotation_is_deterministic_and_assignment_is_preserved(tmp_path) -> None:
    """Requisito: rotação e atribuição. Resultado esperado: duas voltas exatas."""
    jobs = [
        _job(round_number, provider)
        for round_number in (1, 2)
        for provider in DEFAULT_PROVIDER_ORDER
    ]
    assignments = {job.job_id: job.provider for job in jobs}
    scheduler, queue, _, _, sleeps = _scheduler(tmp_path, jobs)

    selected = [_run_and_complete(scheduler) for _ in jobs]

    assert [job.provider for job in selected] == list(DEFAULT_PROVIDER_ORDER) * 2
    assert all(assignments[job.job_id] == job.provider for job in queue.load())
    assert sleeps == []


def test_queue_order_is_preserved_inside_provider(tmp_path) -> None:
    """Requisito: ordem por provider. Resultado esperado: primeiro chunk vem primeiro."""
    configs = _configs()
    configs["gemini"].max_consecutive_requests = 2
    scheduler, _, _, _, _ = _scheduler(
        tmp_path,
        [_job(2, "gemini"), _job(1, "gemini")],
        configs,
    )

    assert _run_and_complete(scheduler).chunk_id == "gemini_2"
    assert _run_and_complete(scheduler).chunk_id == "gemini_1"


def test_unavailable_provider_is_skipped(tmp_path) -> None:
    """Requisito: provider indisponível. Resultado esperado: scheduler escolhe o seguinte."""
    scheduler, _, limiter, _, _ = _scheduler(
        tmp_path,
        [_job(1, "gemini"), _job(1, "groq")],
    )
    limiter.record_rate_limit("gemini", retry_after_seconds=10)

    assert scheduler.next_decision().provider == "groq"


def test_disabled_provider_is_skipped(tmp_path) -> None:
    """Requisito: provider desativado. Resultado esperado: job permanece sem transferência."""
    configs = _configs(gemini=True)
    scheduler, queue, _, _, _ = _scheduler(
        tmp_path,
        [_job(1, "gemini"), _job(1, "groq")],
        configs,
    )

    assert scheduler.next_decision().provider == "groq"
    assert queue.load()[0].provider == "gemini"


def test_one_cooling_provider_does_not_block_others(tmp_path) -> None:
    """Requisito: cooldown isolado. Resultado esperado: outros providers continuam."""
    scheduler, _, limiter, _, _ = _scheduler(
        tmp_path,
        [_job(1, "gemini"), _job(1, "mistral")],
    )
    limiter.record_rate_limit("gemini")

    assert scheduler.next_decision().provider == "mistral"


def test_shortest_wait_when_all_are_unavailable(tmp_path) -> None:
    """Requisito: todos indisponíveis. Resultado esperado: espera positiva mais curta."""
    scheduler, _, limiter, _, _ = _scheduler(
        tmp_path,
        [_job(1, "gemini"), _job(1, "groq")],
    )
    limiter.record_rate_limit("gemini", retry_after_seconds=9)
    limiter.record_rate_limit("groq", retry_after_seconds=4)

    decision = scheduler.next_decision()
    assert decision.action == "wait"
    assert decision.wait_seconds == 4


def test_retry_wait_runs_and_terminal_jobs_are_ignored(tmp_path) -> None:
    """Requisito: estados selecionáveis. Resultado esperado: só retry_wait é executado."""
    scheduler, _, _, _, _ = _scheduler(
        tmp_path,
        [
            _job(1, "gemini", "completed"),
            _job(2, "gemini", "failed"),
            _job(3, "gemini", "retry_wait"),
        ],
    )

    assert scheduler.next_decision().job.chunk_id == "gemini_3"  # type: ignore[union-attr]


def test_valid_transitions_increment_attempt_and_clear_error(tmp_path) -> None:
    """Requisito: transições válidas. Resultado esperado: tentativa e resultado persistem."""
    scheduler, queue, _, _, _ = _scheduler(tmp_path, [_job(1, "gemini")])
    job = scheduler.next_job()
    assert job is not None

    scheduler.mark_running(job)
    assert queue.load()[0].attempt_count == 1
    scheduler.mark_retry_wait(job, "temporary")
    scheduler.mark_running(job)
    scheduler.mark_completed(job, "result.json")

    persisted = queue.load()[0]
    assert persisted.attempt_count == 2
    assert persisted.status == "completed"
    assert persisted.result_file == "result.json"
    assert persisted.last_error == ""


def test_invalid_transitions_are_rejected(tmp_path) -> None:
    """Requisito: transições inválidas. Resultado esperado: ValueError sem persistência."""
    scheduler, _, _, _, _ = _scheduler(tmp_path, [_job(1, "gemini")])
    job = scheduler.next_job()
    assert job is not None

    with pytest.raises(ValueError, match="pending -> completed"):
        scheduler.mark_completed(job, "result.json")
    with pytest.raises(ValueError, match="pending -> failed"):
        scheduler.mark_failed(job, "bad")


def test_errors_are_sanitized_and_bounded(tmp_path) -> None:
    """Requisito: erros seguros. Resultado esperado: segredo oculto e texto limitado."""
    scheduler, queue, _, _, _ = _scheduler(tmp_path, [_job(1, "gemini")])
    job = scheduler.next_job()
    assert job is not None
    scheduler.mark_running(job)
    scheduler.mark_failed(job, "Authorization: Bearer secret-token " + "x" * 2000)

    error = queue.load()[0].last_error
    assert "secret-token" not in error
    assert "[REDACTED]" in error
    assert len(error) == 1000


def test_pause_and_resume_only_target_provider_jobs(tmp_path) -> None:
    """Requisito: pausa e retoma. Resultado esperado: apenas jobs alvo mudam de estado."""
    scheduler, queue, _, _, _ = _scheduler(
        tmp_path,
        [_job(1, "gemini"), _job(2, "gemini", "retry_wait"), _job(1, "groq")],
    )

    assert scheduler.pause_provider("gemini") == 2
    assert [job.status for job in queue.load()] == ["paused", "paused", "pending"]
    assert scheduler.resume_provider("gemini") == 2
    assert [job.status for job in queue.load()] == ["pending", "pending", "pending"]


def test_empty_queue_returns_empty_decision(tmp_path) -> None:
    """Requisito: fila vazia. Resultado esperado: decisão empty sem provider nem sleep."""
    scheduler, _, _, _, sleeps = _scheduler(tmp_path, [])

    decision = scheduler.next_decision()
    assert decision.action == "empty"
    assert decision.job is None
    assert sleeps == []
