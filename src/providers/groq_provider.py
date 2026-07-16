"""Implementa a comunicação com a API oficial Groq."""

import os
from typing import Any

from groq import Groq

from src.core.interfaces import AIProvider, GenerationRequest, GenerationResult


class GroqProvider(AIProvider):
    """Adapta descoberta de modelos e completions Groq ao contrato comum."""

    DEFAULT_MODEL_CANDIDATES = (
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3-32b",
        "moonshotai/kimi-k2-instruct-0905",
        "meta-llama/llama-4-scout-17b-16e-instruct",
    )

    def __init__(
        self,
        model: str | None = None,
        model_candidates: list[str] | None = None,
    ) -> None:
        """Valida a chave e configura preferências opcionais de modelo."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")

        self.model = model
        self.model_candidates = model_candidates
        self.client = Groq(api_key=api_key)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Seleciona um modelo disponível e executa uma única completion."""
        available_models = sorted(
            model.id for model in self.client.models.list().data
        )
        requested_model = self._select_model(request, available_models)

        messages = []
        if request.system_prompt is not None:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        options: dict[str, Any] = {
            "model": requested_model,
            "messages": messages,
        }
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_tokens is not None:
            options["max_tokens"] = request.max_tokens
        if request.require_json:
            options["response_format"] = {"type": "json_object"}

        completion = self.client.chat.completions.create(**options)
        reported_model = getattr(completion, "model", None)
        actual_model = (
            reported_model if isinstance(reported_model, str) else requested_model
        )

        return GenerationResult(
            text=(completion.choices[0].message.content or "").strip(),
            provider="groq",
            requested_model=requested_model,
            actual_model=actual_model,
            usage=self._usage_to_dict(getattr(completion, "usage", None)),
            metadata={"available_models": available_models},
            attempts=[
                {"model": requested_model, "attempt": 1, "success": True}
            ],
        )

    def _select_model(
        self,
        request: GenerationRequest,
        available_models: list[str],
    ) -> str:
        """Aplica a prioridade explícita e depois a ordem dos candidatos."""
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
            raise RuntimeError("No requested Groq model candidate is available")
        return selected

    @staticmethod
    def _usage_to_dict(usage: object) -> dict[str, Any]:
        """Converte a utilização devolvida pelo SDK num dicionário simples."""
        if isinstance(usage, dict):
            return usage
        model_dump = getattr(usage, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(exclude_none=True)
            if isinstance(dumped, dict):
                return dumped
        return {}
