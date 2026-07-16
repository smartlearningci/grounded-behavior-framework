"""Implementa a comunicação HTTP com fallback para OpenRouter Free."""

import os
import time
from typing import Any

import requests

from src.core.interfaces import AIProvider, GenerationRequest, GenerationResult


class OpenRouterProvider(AIProvider):
    """Executa retries e fallback sequencial entre modelos OpenRouter."""

    MODELS_URL = "https://openrouter.ai/api/v1/models"
    CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL_CANDIDATES = (
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "google/gemma-4-26b-a4b-it:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "openai/gpt-oss-20b:free",
        "meta-llama/llama-3.2-3b-instruct:free",
    )
    RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}

    def __init__(
        self,
        model: str | None = None,
        model_candidates: list[str] | None = None,
    ) -> None:
        """Valida a chave e prepara cabeçalhos e preferências de fallback."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")

        self.model = model
        self.model_candidates = model_candidates
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://colab.research.google.com",
            "X-Title": "Cognitive Curriculum Provider Validation",
        }

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Tenta candidatos disponíveis até obter a primeira resposta válida."""
        available_models = self._list_models()
        candidates = self._available_candidates(request, available_models)
        messages = self._build_messages(request)
        attempts: list[dict[str, Any]] = []

        for model in candidates:
            for attempt_number in range(1, 3):
                payload = self._build_payload(
                    request,
                    model,
                    messages,
                )
                response = requests.post(
                    self.CHAT_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=180,
                )

                if response.ok:
                    data = response.json()
                    attempts.append(
                        {
                            "model": model,
                            "attempt": attempt_number,
                            "success": True,
                            "status_code": response.status_code,
                        }
                    )
                    return GenerationResult(
                        text=(
                            data["choices"][0]["message"]["content"] or ""
                        ).strip(),
                        provider="openrouter",
                        requested_model=model,
                        actual_model=data.get("model", model),
                        usage=self._plain_dict(data.get("usage")),
                        metadata={
                            "fallback_strategy": "client_side_sequential",
                            "candidate_models": candidates,
                        },
                        attempts=attempts,
                    )

                retryable = response.status_code in self.RETRYABLE_STATUS_CODES
                failed_attempt: dict[str, Any] = {
                    "model": model,
                    "attempt": attempt_number,
                    "success": False,
                    "status_code": response.status_code,
                    "retryable": retryable,
                }
                if retryable and attempt_number < 2:
                    retry_after = self._extract_retry_after(response)
                    failed_attempt["retry_after_seconds"] = retry_after
                    attempts.append(failed_attempt)
                    time.sleep(retry_after + 1)
                    continue

                attempts.append(failed_attempt)
                break

        summary = ", ".join(
            f"{item['model']}:{item['status_code']}" for item in attempts
        )
        raise RuntimeError(f"All OpenRouter model candidates failed ({summary})")

    def _list_models(self) -> list[str]:
        """Obtém os modelos atualmente publicados pelo OpenRouter."""
        response = requests.get(
            self.MODELS_URL,
            headers=self.headers,
            timeout=60,
        )
        response.raise_for_status()
        return [
            item["id"]
            for item in response.json().get("data", [])
            if item.get("id")
        ]

    def _configured_candidates(self, request: GenerationRequest) -> list[str]:
        """Resolve a lista de candidatos antes de verificar disponibilidade."""
        if request.model is not None:
            return [request.model]
        if request.model_candidates:
            return list(request.model_candidates)
        if self.model is not None:
            return [self.model]
        if self.model_candidates is not None:
            return list(self.model_candidates)
        return list(self.DEFAULT_MODEL_CANDIDATES)

    def _available_candidates(
        self,
        request: GenerationRequest,
        available_models: list[str],
    ) -> list[str]:
        """Filtra candidatos disponíveis preservando a ordem configurada."""
        available_ids = set(available_models)
        candidates = [
            model
            for model in self._configured_candidates(request)
            if model in available_ids
        ]
        if not candidates:
            raise RuntimeError("No requested OpenRouter model candidate is available")
        return candidates

    @staticmethod
    def _build_messages(request: GenerationRequest) -> list[dict[str, str]]:
        """Constrói as mensagens de sistema e utilizador."""
        messages = []
        if request.system_prompt is not None:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        return messages

    @staticmethod
    def _build_payload(
        request: GenerationRequest,
        model: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Constrói o payload de geração para um candidato."""
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.require_json:
            payload["response_format"] = {"type": "json_object"}
        return payload

    @staticmethod
    def _extract_retry_after(response: requests.Response) -> int:
        """Extrai o atraso do cabeçalho, dos metadados ou do valor padrão."""
        header_value = response.headers.get("Retry-After")
        if header_value:
            try:
                return max(1, int(float(header_value)))
            except ValueError:
                pass

        try:
            value = (
                response.json()
                .get("error", {})
                .get("metadata", {})
                .get("retry_after_seconds")
            )
            if value is not None:
                return max(1, int(float(value)))
        except (AttributeError, TypeError, ValueError):
            pass
        return 12

    @staticmethod
    def _plain_dict(value: object) -> dict[str, Any]:
        """Normaliza metadados HTTP que sejam representados por dicionários."""
        return value if isinstance(value, dict) else {}
