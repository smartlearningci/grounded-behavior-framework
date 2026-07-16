"""Implementa a geração de texto através da API oficial Google Gemini."""

import os

from google import genai
from google.genai import types

from src.core.interfaces import (
    AIProvider,
    GenerationRequest,
    GenerationResult,
)


class GeminiProvider(AIProvider):
    """Adapta o cliente Gemini ao contrato comum ``AIProvider``.

    O objetivo é enviar pedidos estruturados ao modelo configurado usando a
    chave ``GEMINI_API_KEY`` e devolver texto com metadados de proveniência.
    """

    DEFAULT_MODEL = "gemini-3.1-flash-lite"

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        """Valida a chave da API e cria o cliente para o modelo selecionado.

        Lança ``ValueError`` antes de criar o cliente quando a variável de
        ambiente ``GEMINI_API_KEY`` não está definida ou está vazia.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

        self.model = model
        self.client = genai.Client(api_key=api_key)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Gera texto com os parâmetros comuns suportados pela API Gemini."""
        requested_model = request.model
        if requested_model is None and request.model_candidates:
            requested_model = request.model_candidates[0]
        if requested_model is None:
            requested_model = self.model

        config_options = {}
        if request.system_prompt is not None:
            config_options["system_instruction"] = request.system_prompt
        if request.temperature is not None:
            config_options["temperature"] = request.temperature
        if request.max_tokens is not None:
            config_options["max_output_tokens"] = request.max_tokens
        if request.require_json:
            config_options["response_mime_type"] = "application/json"

        generation_options = {
            "model": requested_model,
            "contents": request.prompt,
        }
        if config_options:
            generation_options["config"] = types.GenerateContentConfig(
                **config_options
            )

        generated = self.client.models.generate_content(**generation_options)

        reported_model = getattr(generated, "model_version", None)
        actual_model = (
            reported_model if isinstance(reported_model, str) else requested_model
        )
        response_id = getattr(generated, "response_id", None)
        metadata = {}
        if isinstance(response_id, str):
            metadata["response_id"] = response_id

        return GenerationResult(
            text=(generated.text or "").strip(),
            provider="gemini",
            requested_model=requested_model,
            actual_model=actual_model,
            usage=self._usage_to_dict(getattr(generated, "usage_metadata", None)),
            metadata=metadata,
            attempts=[
                {
                    "model": requested_model,
                    "attempt": 1,
                    "success": True,
                }
            ],
        )

    @staticmethod
    def _usage_to_dict(usage: object) -> dict[str, object]:
        """Converte os metadados de utilização do SDK num dicionário simples."""
        if isinstance(usage, dict):
            return usage

        model_dump = getattr(usage, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(exclude_none=True)
            if isinstance(dumped, dict):
                return dumped

        return {}
