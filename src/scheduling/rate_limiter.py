"""Aplica limites locais por provider sem dormir nem chamar APIs."""

import time
from collections.abc import Callable
from datetime import datetime, time as datetime_time, timedelta, timezone
from math import inf
from typing import Any

from .config import ProviderLimitConfig


class ProviderRateLimiter:
    """Mantém estado temporal testável para limites configurados em YAML."""

    def __init__(
        self,
        provider_configs: dict[str, ProviderLimitConfig],
        time_source: Callable[[], float] = time.monotonic,
        sleep_function: Callable[[float], None] = time.sleep,
        utc_now_source: Callable[[], datetime] | None = None,
    ) -> None:
        """Recebe configurações, relógio monotónico, sleep e relógio UTC."""
        self.provider_configs = provider_configs
        self.time_source = time_source
        self.sleep_function = sleep_function
        self.utc_now_source = utc_now_source or (
            lambda: datetime.now(timezone.utc)
        )
        self.last_request_timestamps: dict[str, float] = {}
        self.minute_request_timestamps: dict[str, list[float]] = {
            provider: [] for provider in provider_configs
        }
        self.daily_request_counts: dict[str, dict[str, object]] = {
            provider: {"date": self._utc_now().date().isoformat(), "count": 0}
            for provider in provider_configs
        }
        self.cooldown_until: dict[str, float] = {}
        self.consecutive_request_counts: dict[str, int] = {
            provider: 0 for provider in provider_configs
        }
        self.last_selected_provider: str | None = None

    def can_run(self, provider: str, now: float | None = None) -> bool:
        """Indica elegibilidade imediata sem executar qualquer espera."""
        return self.seconds_until_available(provider, now) == 0

    def seconds_until_available(
        self,
        provider: str,
        now: float | None = None,
    ) -> float:
        """Calcula a maior espera imposta pelos limites do provider."""
        config = self._config(provider)
        if not config.enabled:
            return inf
        current = self.time_source() if now is None else now
        waits: list[float] = [0.0]

        cooldown = self.cooldown_until.get(provider)
        if cooldown is not None:
            waits.append(max(0.0, cooldown - current))

        last_request = self.last_request_timestamps.get(provider)
        if last_request is not None:
            waits.append(
                max(0.0, last_request + config.min_delay_seconds - current)
            )

        recent = self._recent_minute_requests(provider, current)
        minute_limit = config.max_requests_per_minute
        if minute_limit is not None and len(recent) >= minute_limit:
            blocking_timestamp = recent[len(recent) - minute_limit]
            waits.append(max(0.0, blocking_timestamp + 60.0 - current))

        daily_count = self._daily_count(provider)
        if (
            config.max_requests_per_day is not None
            and daily_count >= config.max_requests_per_day
        ):
            waits.append(self._seconds_until_next_utc_day())

        if (
            self.last_selected_provider == provider
            and self.consecutive_request_counts.get(provider, 0)
            >= config.max_consecutive_requests
        ):
            waits.append(inf)
        return max(waits)

    def record_request(
        self,
        provider: str,
        timestamp: float | None = None,
    ) -> None:
        """Regista uma seleção para limites temporal, diário e consecutivo."""
        self._config(provider)
        current = self.time_source() if timestamp is None else timestamp
        self.reset_consecutive_if_provider_changes(provider)
        self.last_request_timestamps[provider] = current
        recent = self._recent_minute_requests(provider, current)
        recent.append(current)
        self.minute_request_timestamps[provider] = recent
        daily = self._daily_state(provider)
        daily["count"] = int(daily["count"]) + 1
        self.consecutive_request_counts[provider] = (
            self.consecutive_request_counts.get(provider, 0) + 1
        )

    def record_rate_limit(
        self,
        provider: str,
        retry_after_seconds: float | None = None,
        timestamp: float | None = None,
    ) -> None:
        """Inicia cooldown, dando prioridade a Retry-After quando presente."""
        config = self._config(provider)
        current = self.time_source() if timestamp is None else timestamp
        if retry_after_seconds is None:
            delay = config.cooldown_after_rate_limit_seconds
        else:
            if retry_after_seconds < 0:
                raise ValueError("retry_after_seconds must be non-negative")
            delay = float(retry_after_seconds)
        self.cooldown_until[provider] = max(
            self.cooldown_until.get(provider, current),
            current + delay,
        )

    def reset_consecutive_if_provider_changes(self, provider: str) -> None:
        """Reinicia contadores quando a seleção roda para outro provider."""
        self._config(provider)
        if self.last_selected_provider == provider:
            return
        if self.last_selected_provider is not None:
            self.consecutive_request_counts[self.last_selected_provider] = 0
        self.consecutive_request_counts[provider] = 0
        self.last_selected_provider = provider

    def export_state(self) -> dict[str, object]:
        """Exporta estado simples para persistência futura ou preview."""
        return {
            "last_request_timestamps": dict(self.last_request_timestamps),
            "minute_request_timestamps": {
                provider: list(timestamps)
                for provider, timestamps in self.minute_request_timestamps.items()
            },
            "daily_request_counts": {
                provider: dict(state)
                for provider, state in self.daily_request_counts.items()
            },
            "cooldown_until": dict(self.cooldown_until),
            "consecutive_request_counts": dict(self.consecutive_request_counts),
            "last_selected_provider": self.last_selected_provider,
        }

    def restore_state(self, state: dict[str, object]) -> None:
        """Restaura um estado anteriormente exportado e normaliza números."""
        if not isinstance(state, dict):
            raise ValueError("Rate limiter state must be a mapping")
        try:
            self.last_request_timestamps = {
                str(provider): float(timestamp)
                for provider, timestamp in _mapping(
                    state, "last_request_timestamps"
                ).items()
            }
            self.minute_request_timestamps = {
                str(provider): [float(value) for value in timestamps]
                for provider, timestamps in _mapping(
                    state, "minute_request_timestamps"
                ).items()
            }
            self.daily_request_counts = {
                str(provider): {
                    "date": str(values["date"]),
                    "count": int(values["count"]),
                }
                for provider, values in _mapping(
                    state, "daily_request_counts"
                ).items()
            }
            self.cooldown_until = {
                str(provider): float(timestamp)
                for provider, timestamp in _mapping(
                    state, "cooldown_until"
                ).items()
            }
            self.consecutive_request_counts = {
                str(provider): int(count)
                for provider, count in _mapping(
                    state, "consecutive_request_counts"
                ).items()
            }
            selected = state.get("last_selected_provider")
            self.last_selected_provider = (
                None if selected is None else str(selected)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Malformed rate limiter state: {exc}") from exc
        for provider in self.provider_configs:
            self.minute_request_timestamps.setdefault(provider, [])
            self.daily_request_counts.setdefault(
                provider,
                {"date": self._utc_now().date().isoformat(), "count": 0},
            )
            self.consecutive_request_counts.setdefault(provider, 0)

    def _config(self, provider: str) -> ProviderLimitConfig:
        """Obtém configuração ou rejeita um provider desconhecido."""
        try:
            return self.provider_configs[provider]
        except KeyError as exc:
            raise KeyError(f"Provider has no rate-limit configuration: {provider}") from exc

    def _recent_minute_requests(
        self,
        provider: str,
        now: float,
    ) -> list[float]:
        """Remove timestamps que já saíram da janela deslizante de 60 segundos."""
        recent = [
            timestamp
            for timestamp in self.minute_request_timestamps.get(provider, [])
            if timestamp > now - 60.0
        ]
        self.minute_request_timestamps[provider] = recent
        return recent

    def _daily_state(self, provider: str) -> dict[str, object]:
        """Reinicia o contador quando muda a data UTC."""
        today = self._utc_now().date().isoformat()
        state = self.daily_request_counts.setdefault(
            provider,
            {"date": today, "count": 0},
        )
        if state.get("date") != today:
            state = {"date": today, "count": 0}
            self.daily_request_counts[provider] = state
        return state

    def _daily_count(self, provider: str) -> int:
        """Devolve o contador válido para a data UTC atual."""
        return int(self._daily_state(provider)["count"])

    def _seconds_until_next_utc_day(self) -> float:
        """Calcula a duração restante até à meia-noite UTC seguinte."""
        now = self._utc_now()
        tomorrow = datetime.combine(
            now.date() + timedelta(days=1),
            datetime_time.min,
            tzinfo=timezone.utc,
        )
        return max(0.0, (tomorrow - now).total_seconds())

    def _utc_now(self) -> datetime:
        """Normaliza o relógio civil injetado para UTC."""
        value = self.utc_now_source()
        if value.tzinfo is None:
            raise ValueError("UTC clock must return a timezone-aware datetime")
        return value.astimezone(timezone.utc)


def _mapping(state: dict[str, object], key: str) -> dict[Any, Any]:
    """Obtém um submapeamento obrigatório do estado exportado."""
    value = state.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Rate limiter state '{key}' must be a mapping")
    return value
