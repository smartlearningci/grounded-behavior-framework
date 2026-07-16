"""Implementa a comunicação HTTP com a API Mistral."""

import os
from typing import Any

import requests

from src.core.interfaces import AIProvider, GenerationRequest, GenerationResult


class MistralProvider(AIProvider):
    """Adapta os endpoints HTTP da Mistral ao contrato comum de geração."""

    MODELS_URL = "https://api.mistral.ai/v1/models"
    CHAT_URL = "https://api.mistral.ai/v1/chat/completions"
    DEFAULT_MODEL_CANDIDATES = (
        "mistral-small-latest",
        "mistral-small-2603",
        "ministral-8b-latest",
        "ministral-3b-latest",
    )

    def __init__(
        self,
        model: str | None = None,
        model_candidates: list[str] | None = None,
    ) -> None:
        """Valida a chave e prepara cabeçalhos e preferências de modelo."""
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is not set")

        self.model = model
        self.model_candidates = model_candidates
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Descobre um modelo e efetua uma única chamada HTTP de geração."""
        available_models = self._list_models()
        requested_model = self._select_model(request, available_models)
        payload = self._build_payload(request, requested_model)

        response = requests.post(
            self.CHAT_URL,
            headers=self.headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        return GenerationResult(
            text=(data["choices"][0]["message"]["content"] or "").strip(),
            provider="mistral",
            requested_model=requested_model,
            actual_model=data.get("model", requested_model),
            usage=self._plain_dict(data.get("usage")),
            metadata={"available_models": available_models},
            attempts=[
                {
                    "model": requested_model,
                    "attempt": 1,
                    "success": True,
                    "status_code": response.status_code,
                }
            ],
        )

    def _list_models(self) -> list[str]:
        """Obtém e ordena os identificadores de modelos disponíveis."""
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
    ) -> str:
        """Seleciona um modelo explícito ou o primeiro candidato disponível."""
        if request.model is not None:
            return request.model
        if request.model_candidates:
            candidates = request.model_candidates
        elif self.model is not None:
            return self.model
        elif self.model_candidates is not None:
            candidates = self.model_candidates
        else:
            candidates = self.DEFAULT_MODEL_CANDIDATES

        selected = next(
            (candidate for candidate in candidates if candidate in available_models),
            None,
        )
        if selected is None:
            raise RuntimeError("No requested Mistral model candidate is available")
        return selected

    @staticmethod
    def _build_payload(
        request: GenerationRequest,
        requested_model: str,
    ) -> dict[str, Any]:
        """Constrói o payload chat compatível com o notebook validado."""
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
    def _plain_dict(value: object) -> dict[str, Any]:
        """Normaliza metadados HTTP que sejam representados por dicionários."""
        return value if isinstance(value, dict) else {}
