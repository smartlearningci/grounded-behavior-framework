"""Implementa a comunicação HTTP com a API Cerebras."""

import os
import time
from typing import Any

import requests

from src.core.interfaces import AIProvider, GenerationRequest, GenerationResult


class CerebrasProvider(AIProvider):
    """Seleciona um modelo textual e repete chamadas transitórias à Cerebras."""

    MODELS_URL = "https://api.cerebras.ai/v1/models"
    CHAT_URL = "https://api.cerebras.ai/v1/chat/completions"
    DEFAULT_MODEL_CANDIDATES = (
        "gemma-4-31b",
        "zai-glm-4.7",
        "gpt-oss-120b",
        "qwen-3-235b-a22b-instruct-2507",
    )
    EXCLUDED_TEXT_MODEL_TERMS = (
        "embed",
        "rerank",
        "guard",
        "safety",
        "moderation",
        "ocr",
        "audio",
        "image",
    )
    RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}

    def __init__(
        self,
        model: str | None = None,
        model_candidates: list[str] | None = None,
    ) -> None:
        """Valida a chave e prepara cabeçalhos e preferências de modelo."""
        api_key = os.getenv("CEREBRAS_API_KEY")
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY environment variable is not set")

        self.model = model
        self.model_candidates = model_candidates
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Seleciona um modelo e repete apenas esse modelo até três vezes."""
        available_models = self._list_models()
        requested_model, selection = self._select_model(request, available_models)
        payload = self._build_payload(request, requested_model)
        attempts: list[dict[str, Any]] = []

        for attempt_number in range(1, 4):
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
                        "model": requested_model,
                        "attempt": attempt_number,
                        "success": True,
                        "status_code": response.status_code,
                    }
                )
                return GenerationResult(
                    text=(data["choices"][0]["message"]["content"] or "").strip(),
                    provider="cerebras",
                    requested_model=requested_model,
                    actual_model=data.get("model", requested_model),
                    usage=self._plain_dict(data.get("usage")),
                    metadata={
                        "available_models": available_models,
                        "model_selection": selection,
                    },
                    attempts=attempts,
                )

            retryable = response.status_code in self.RETRYABLE_STATUS_CODES
            failed_attempt: dict[str, Any] = {
                "model": requested_model,
                "attempt": attempt_number,
                "success": False,
                "status_code": response.status_code,
                "retryable": retryable,
            }
            if retryable and attempt_number < 3:
                retry_after = self._extract_retry_after(response)
                failed_attempt["retry_after_seconds"] = retry_after
                attempts.append(failed_attempt)
                time.sleep(retry_after + 1)
                continue

            attempts.append(failed_attempt)
            response.raise_for_status()

        raise RuntimeError("Cerebras did not respond after three attempts")

    def _list_models(self) -> list[str]:
        """Obtém e ordena os identificadores de modelos Cerebras."""
        response = requests.get(
            self.MODELS_URL,
            headers=self.headers,
            timeout=60,
        )
        response.raise_for_status()
        return sorted(
            item["id"]
            for item in response.json().get("data", [])
            if item.get("id")
        )

    def _select_model(
        self,
        request: GenerationRequest,
        available_models: list[str],
    ) -> tuple[str, str]:
        """Seleciona por prioridade ou recorre ao primeiro modelo textual."""
        if request.model is not None:
            return request.model, "explicit"
        if request.model_candidates:
            candidates = request.model_candidates
        elif self.model is not None:
            return self.model, "configured"
        elif self.model_candidates is not None:
            candidates = self.model_candidates
        else:
            candidates = self.DEFAULT_MODEL_CANDIDATES

        selected = next(
            (candidate for candidate in candidates if candidate in available_models),
            None,
        )
        if selected is not None:
            return selected, "candidate"

        textual_models = [
            model
            for model in available_models
            if not any(
                term in model.lower() for term in self.EXCLUDED_TEXT_MODEL_TERMS
            )
        ]
        if not textual_models:
            raise RuntimeError("No textual Cerebras model is available")
        return textual_models[0], "textual_fallback"

    @staticmethod
    def _build_payload(
        request: GenerationRequest,
        requested_model: str,
    ) -> dict[str, Any]:
        """Constrói o payload chat usado pelo notebook validado."""
        messages = []
        if request.system_prompt is not None:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, Any] = {
            "model": requested_model,
            "messages": messages,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.require_json:
            payload["response_format"] = {"type": "json_object"}
        return payload

    @staticmethod
    def _extract_retry_after(response: requests.Response) -> int:
        """Extrai Retry-After ou devolve os dez segundos validados."""
        header_value = response.headers.get("Retry-After")
        if header_value:
            try:
                return max(1, int(float(header_value)))
            except ValueError:
                pass
        return 10

    @staticmethod
    def _plain_dict(value: object) -> dict[str, Any]:
        """Normaliza metadados HTTP que sejam representados por dicionários."""
        return value if isinstance(value, dict) else {}
