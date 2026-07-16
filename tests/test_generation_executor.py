"""Testes do executor retomável com providers totalmente simulados."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from src.core.interfaces import GenerationResult
from src.execution.config import ProviderRuntimeConfig
from src.execution.executor import GenerationExecutor
from src.execution.result_writer import ResultWriter
from src.scheduling.config import ProviderLimitConfig
from src.scheduling.models import GenerationJob, utc_now_iso
from src.scheduling.queue import GenerationQueue
from src.scheduling.rate_limiter import ProviderRateLimiter
from src.scheduling.scheduler import DEFAULT_PROVIDER_ORDER, RoundRobinScheduler


class FakeClock:
    """Relógio e sleep simulados para testes determinísticos."""

    def __init__(self):
        self.value = 0.0
        self.utc = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.sleeps = []

    def monotonic(self):
        return self.value

    def utc_now(self):
        return self.utc

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds
        self.utc += timedelta(seconds=seconds)


def _job(number, provider, model="model-a", status="pending", attempt=0):
    now = utc_now_iso()
    chunk = f"{provider}_{number}"
    return GenerationJob(
        f"job_{chunk}", number, "batch", chunk, provider, model, "n1_v1", "train",
        20, f"{chunk}.prompt.txt", f"{chunk}.json", status, attempt, now, now, "", "",
    )


def _setup(tmp_path, jobs, behavior=None, max_attempts=3, max_consecutive=10):
    queue = GenerationQueue(tmp_path / "jobs.jsonl")
    queue.save(jobs)
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for job in jobs:
        (prompts / job.prompt_file).write_text(f"prompt {job.chunk_id}", encoding="utf-8")
    limits = {
        provider: ProviderLimitConfig(
            provider, True, 0, None, None, max_consecutive, max_attempts, 7
        )
        for provider in DEFAULT_PROVIDER_ORDER
    }
    runtime = {
        provider: ProviderRuntimeConfig(
            provider, None if provider == "gemini" else "system", 0.8,
            None if provider == "gemini" else 4000, True,
            str(tmp_path / "raw" / provider), True, True, 5,
        )
        for provider in DEFAULT_PROVIDER_ORDER
    }
    clock = FakeClock()
    limiter = ProviderRateLimiter(
        limits, clock.monotonic, clock.sleep, utc_now_source=clock.utc_now
    )
    scheduler = RoundRobinScheduler(queue, limits, limiter)
    calls = []
    instances = {}

    def factory(provider):
        calls.append(provider)
        action = behavior.get(provider) if behavior else None
        if isinstance(action, Exception):
            raise action
        instance = instances.setdefault(provider, Mock())
        if callable(action):
            instance.generate.side_effect = action
        else:
            instance.generate.return_value = GenerationResult(
                text=f"raw {provider}", provider=provider,
                requested_model="model-a", actual_model="actual", metadata={"ok": True},
            )
        return instance

    executor = GenerationExecutor(
        queue, scheduler, limits, runtime, ResultWriter(runtime), prompts,
        tmp_path / "limiter.json", clock.monotonic, clock.sleep, factory,
    )
    return executor, queue, limiter, clock, calls, instances


def test_round_robin_lazy_creation_requests_and_assignment(tmp_path) -> None:
    """Requisito: rotação e criação lazy. Resultado esperado: cinco providers na ordem original."""
    jobs = [_job(1, provider) for provider in DEFAULT_PROVIDER_ORDER]
    executor, queue, _, _, calls, instances = _setup(tmp_path, jobs)

    summary = executor.run(5)

    assert [record.provider for record in executor.last_records] == list(DEFAULT_PROVIDER_ORDER)
    assert calls == list(DEFAULT_PROVIDER_ORDER)
    assert summary.jobs_completed == 5
    assert all(job.status == "completed" for job in queue.load())
    assert [job.provider for job in queue.load()] == list(DEFAULT_PROVIDER_ORDER)
    groq_request = instances["groq"].generate.call_args.args[0]
    assert groq_request.system_prompt == "system"
    assert groq_request.temperature == 0.8 and groq_request.max_tokens == 4000
    assert groq_request.require_json and groq_request.model == "model-a"


def test_provider_cache_and_placeholder_model(tmp_path) -> None:
    """Requisito: cache e placeholder. Resultado esperado: uma instância e model None."""
    executor, _, _, _, calls, instances = _setup(
        tmp_path, [_job(1, "gemini", "provider-selected"), _job(2, "gemini", "")]
    )

    executor.run(2)

    assert calls == ["gemini"]
    assert instances["gemini"].generate.call_count == 2
    assert all(call.args[0].model is None for call in instances["gemini"].generate.call_args_list)


def test_temporary_failure_retries_then_maximum_attempt_fails(tmp_path) -> None:
    """Requisito: retries limitados. Resultado esperado: retry_wait antes de failed."""
    def timeout(_request):
        raise TimeoutError("temporary")

    executor, queue, _, _, _, _ = _setup(
        tmp_path, [_job(1, "gemini")], {"gemini": timeout}, max_attempts=3
    )
    first = executor.run_one(queue.load()[0])
    assert first.status == "retry_wait" and queue.load()[0].attempt_count == 1
    job = queue.load()[0]
    job.attempt_count = 2
    queue.update_job(job)
    second = executor.run_one(queue.load()[0])
    assert second.status == "failed" and queue.load()[0].attempt_count == 3


def test_rate_limit_sets_retry_after_cooldown(tmp_path) -> None:
    """Requisito: 429 com Retry-After. Resultado esperado: retry_wait e cooldown de 11 segundos."""
    class RateError(Exception):
        status_code = 429
        response = type("Response", (), {"status_code": 429, "headers": {"Retry-After": "11"}})()

    def limited(_request):
        raise RateError("limited")

    executor, queue, limiter, _, _, _ = _setup(
        tmp_path, [_job(1, "gemini")], {"gemini": limited}
    )
    record = executor.run_one(queue.load()[0])

    assert record.status == "retry_wait"
    assert limiter.cooldown_until["gemini"] == 11


def test_missing_key_pauses_provider_and_continues_others(tmp_path) -> None:
    """Requisito: chave ausente isolada. Resultado esperado: Gemini pausa e Groq conclui."""
    jobs = [_job(1, "gemini"), _job(2, "gemini"), _job(1, "groq")]
    executor, queue, _, _, _, _ = _setup(
        tmp_path, jobs,
        {"gemini": ValueError("GEMINI_API_KEY environment variable is not set")},
    )

    summary = executor.run(2)

    states = {(job.provider, job.chunk_id): job.status for job in queue.load()}
    assert summary.jobs_failed == 1 and summary.jobs_completed == 1
    assert states[("gemini", "gemini_2")] == "paused"
    assert states[("groq", "groq_1")] == "completed"


def test_existing_valid_result_skips_api_and_invalid_result_fails(tmp_path) -> None:
    """Requisito: resultados existentes seguros. Resultado esperado: válido salta API e inválido falha."""
    executor, queue, _, _, calls, _ = _setup(tmp_path, [_job(1, "gemini")])
    path = executor.result_writer.success_path(queue.load()[0])
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
    record = executor.run_one(queue.load()[0])
    assert record.status == "skipped_existing" and calls == []

    executor2, queue2, _, _, calls2, _ = _setup(tmp_path / "other", [_job(2, "gemini")])
    bad = executor2.result_writer.success_path(queue2.load()[0])
    bad.parent.mkdir(parents=True)
    bad.write_text("not-json", encoding="utf-8")
    record2 = executor2.run_one(queue2.load()[0])
    assert record2.status == "failed" and "valid JSON" in record2.error and calls2 == []


def test_wait_uses_injected_sleep_and_state_is_persisted(tmp_path) -> None:
    """Requisito: espera no executor. Resultado esperado: sleep injetado e estado atómico persistido."""
    executor, _, limiter, clock, _, _ = _setup(tmp_path, [_job(1, "gemini")])
    limiter.record_rate_limit("gemini", retry_after_seconds=3)

    summary = executor.run(1)

    assert summary.jobs_completed == 1
    assert clock.sleeps == [3]
    assert executor.limiter_state_path.is_file()


def test_dry_run_never_mutates_instantiates_or_sleeps(tmp_path) -> None:
    """Requisito: dry-run puro. Resultado esperado: ordem prevista com bytes e dependências intactos."""
    jobs = [_job(1, provider) for provider in DEFAULT_PROVIDER_ORDER]
    executor, queue, _, clock, calls, _ = _setup(tmp_path, jobs)
    original = queue.path.read_bytes()

    summary = executor.run(5, dry_run=True)

    assert [record.provider for record in executor.last_records] == list(DEFAULT_PROVIDER_ORDER)
    assert all(record.status == "dry_run" for record in executor.last_records)
    assert summary.jobs_started == 0 and calls == [] and clock.sleeps == []
    assert queue.path.read_bytes() == original


def test_interrupted_running_job_is_reset_and_keyboard_interrupt_recovers(tmp_path) -> None:
    """Requisito: interrupção retomável. Resultado esperado: nenhum job permanece running."""
    def interrupt(_request):
        raise KeyboardInterrupt

    executor, queue, _, _, _, _ = _setup(
        tmp_path, [_job(1, "gemini", status="running")], {"gemini": interrupt}
    )

    with pytest.raises(KeyboardInterrupt):
        executor.run(1)
    assert queue.load()[0].status == "pending"
    assert executor.limiter_state_path.exists()


def test_stop_on_error_and_max_jobs(tmp_path) -> None:
    """Requisito: limites da passagem. Resultado esperado: primeiro erro interrompe e max_jobs limita sucessos."""
    def permanent(_request):
        raise ValueError("bad request")

    executor, _, _, _, _, _ = _setup(
        tmp_path, [_job(1, "gemini"), _job(1, "groq")], {"gemini": permanent}
    )
    summary = executor.run(2, stop_on_error=True)
    assert len(executor.last_records) == 1 and summary.stopped_reason == "stop_on_error"

    executor2, _, _, _, _, _ = _setup(
        tmp_path / "limited", [_job(1, "gemini"), _job(1, "groq")]
    )
    executor2.run(1)
    assert len(executor2.last_records) == 1
