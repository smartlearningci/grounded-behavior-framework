"""Testes unitários do limitador local por provider."""

from datetime import datetime, timedelta, timezone
from math import isinf

import pytest

from src.scheduling.config import ProviderLimitConfig
from src.scheduling.rate_limiter import ProviderRateLimiter


class FakeClock:
    """Relógio monotónico e UTC avançável em conjunto."""

    def __init__(self) -> None:
        self.value = 0.0
        self.utc_value = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)

    def monotonic(self) -> float:
        return self.value

    def utc_now(self) -> datetime:
        return self.utc_value

    def advance(self, seconds: float) -> None:
        self.value += seconds
        self.utc_value += timedelta(seconds=seconds)


def _config(provider: str = "gemini", **overrides: object) -> ProviderLimitConfig:
    values: dict[str, object] = {
        "provider": provider,
        "enabled": True,
        "min_delay_seconds": 0.0,
        "max_requests_per_minute": None,
        "max_requests_per_day": None,
        "max_consecutive_requests": 10,
        "max_job_attempts": 3,
        "cooldown_after_rate_limit_seconds": 60.0,
    }
    values.update(overrides)
    return ProviderLimitConfig(**values)  # type: ignore[arg-type]


def _limiter(
    clock: FakeClock,
    configs: dict[str, ProviderLimitConfig],
    sleep_calls: list[float] | None = None,
) -> ProviderRateLimiter:
    calls = sleep_calls if sleep_calls is not None else []
    return ProviderRateLimiter(
        configs,
        time_source=clock.monotonic,
        sleep_function=calls.append,
        utc_now_source=clock.utc_now,
    )


def test_initial_availability_and_no_sleep() -> None:
    """Requisito: disponibilidade inicial. Resultado esperado: zero espera sem sleep."""
    clock = FakeClock()
    calls: list[float] = []
    limiter = _limiter(clock, {"gemini": _config()}, calls)

    assert limiter.can_run("gemini")
    assert limiter.seconds_until_available("gemini") == 0
    assert calls == []


def test_minimum_delay() -> None:
    """Requisito: atraso mínimo. Resultado esperado: provider aguarda o restante."""
    clock = FakeClock()
    limiter = _limiter(clock, {"gemini": _config(min_delay_seconds=6)})
    limiter.record_request("gemini")

    assert limiter.seconds_until_available("gemini") == 6
    clock.advance(6)
    assert limiter.can_run("gemini")


def test_per_minute_limit() -> None:
    """Requisito: limite por minuto. Resultado esperado: janela deslizante de 60 s."""
    clock = FakeClock()
    limiter = _limiter(
        clock,
        {"gemini": _config(max_requests_per_minute=2)},
    )
    limiter.record_request("gemini")
    clock.advance(1)
    limiter.record_request("gemini")

    assert limiter.seconds_until_available("gemini") == 59
    clock.advance(59)
    assert limiter.can_run("gemini")


def test_daily_limit_resets_at_utc_midnight() -> None:
    """Requisito: limite diário UTC. Resultado esperado: desbloqueio à meia-noite."""
    clock = FakeClock()
    limiter = _limiter(clock, {"gemini": _config(max_requests_per_day=1)})
    limiter.record_request("gemini")

    assert limiter.seconds_until_available("gemini") == 12 * 60 * 60
    clock.advance(12 * 60 * 60)
    assert limiter.can_run("gemini")


def test_cooldown_and_retry_after_precedence() -> None:
    """Requisito: cooldown e Retry-After. Resultado esperado: cabeçalho define espera."""
    clock = FakeClock()
    limiter = _limiter(
        clock,
        {"gemini": _config(cooldown_after_rate_limit_seconds=60)},
    )
    limiter.record_rate_limit("gemini")
    assert limiter.seconds_until_available("gemini") == 60

    clock.advance(60)
    limiter.record_rate_limit("gemini", retry_after_seconds=17)
    assert limiter.seconds_until_available("gemini") == 17


def test_disabled_provider() -> None:
    """Requisito: provider desativado. Resultado esperado: nunca fica elegível."""
    clock = FakeClock()
    limiter = _limiter(clock, {"manual": _config("manual", enabled=False)})

    assert not limiter.can_run("manual")
    assert isinf(limiter.seconds_until_available("manual"))


def test_maximum_consecutive_requests_resets_on_provider_change() -> None:
    """Requisito: máximo consecutivo. Resultado esperado: rotação repõe elegibilidade."""
    clock = FakeClock()
    configs = {
        "gemini": _config(max_consecutive_requests=1),
        "groq": _config("groq", max_consecutive_requests=1),
    }
    limiter = _limiter(clock, configs)
    limiter.record_request("gemini")

    assert isinf(limiter.seconds_until_available("gemini"))
    limiter.record_request("groq")
    assert limiter.can_run("gemini")


def test_shortest_wait_is_observable_without_sleep() -> None:
    """Requisito: espera mais curta. Resultado esperado: tempos comparáveis pelo scheduler."""
    clock = FakeClock()
    configs = {"gemini": _config(), "groq": _config("groq")}
    limiter = _limiter(clock, configs)
    limiter.record_rate_limit("gemini", retry_after_seconds=9)
    limiter.record_rate_limit("groq", retry_after_seconds=3)

    waits = [
        limiter.seconds_until_available("gemini"),
        limiter.seconds_until_available("groq"),
    ]
    assert min(waits) == 3


def test_export_and_restore() -> None:
    """Requisito: estado exportável. Resultado esperado: restauro preserva limites."""
    clock = FakeClock()
    configs = {"gemini": _config(min_delay_seconds=6)}
    original = _limiter(clock, configs)
    original.record_request("gemini")
    original.record_rate_limit("gemini", retry_after_seconds=13)

    restored = _limiter(clock, configs)
    restored.restore_state(original.export_state())

    assert restored.export_state() == original.export_state()
    assert restored.seconds_until_available("gemini") == 13


def test_negative_retry_after_is_rejected() -> None:
    """Requisito: Retry-After válido. Resultado esperado: valor negativo é rejeitado."""
    clock = FakeClock()
    limiter = _limiter(clock, {"gemini": _config()})

    with pytest.raises(ValueError, match="non-negative"):
        limiter.record_rate_limit("gemini", retry_after_seconds=-1)
