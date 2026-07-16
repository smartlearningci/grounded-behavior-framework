"""Testes do contrato estável de comunicação com providers."""

from dataclasses import fields
from inspect import signature

import pytest

from src.core.interfaces import (
    AIProvider,
    GenerationRequest,
    GenerationResult,
)


def test_generation_request_has_only_the_frozen_fields():
    """O pedido contém apenas os sete parâmetros comuns acordados."""
    assert [item.name for item in fields(GenerationRequest)] == [
        "prompt",
        "system_prompt",
        "model",
        "model_candidates",
        "temperature",
        "max_tokens",
        "require_json",
    ]

    request = GenerationRequest(prompt="Generate")

    assert request.system_prompt is None
    assert request.model is None
    assert request.model_candidates == []
    assert request.temperature is None
    assert request.max_tokens is None
    assert request.require_json is False


def test_generation_result_has_only_the_frozen_fields():
    """O resultado contém texto, proveniência e metadados operacionais."""
    assert [item.name for item in fields(GenerationResult)] == [
        "text",
        "provider",
        "requested_model",
        "actual_model",
        "usage",
        "metadata",
        "attempts",
    ]

    result = GenerationResult(text="Generated", provider="fake")

    assert result.requested_model is None
    assert result.actual_model is None
    assert result.usage == {}
    assert result.metadata == {}
    assert result.attempts == []


def test_mutable_defaults_are_not_shared_between_instances():
    """Listas e dicionários pertencem apenas à instância que os recebeu."""
    first_request = GenerationRequest(prompt="First")
    second_request = GenerationRequest(prompt="Second")
    first_result = GenerationResult(text="First", provider="fake")
    second_result = GenerationResult(text="Second", provider="fake")

    first_request.model_candidates.append("model-a")
    first_result.usage["total_tokens"] = 1
    first_result.attempts.append({"success": True})

    assert second_request.model_candidates == []
    assert second_result.usage == {}
    assert second_result.attempts == []


def test_ai_provider_requires_generate_request_result_method():
    """AIProvider não pode ser instanciado sem implementar o método final."""
    assert list(signature(AIProvider.generate).parameters) == ["self", "request"]
    assert signature(AIProvider.generate).return_annotation is GenerationResult

    with pytest.raises(TypeError):
        AIProvider()

    class FakeProvider(AIProvider):
        def generate(self, request: GenerationRequest) -> GenerationResult:
            return GenerationResult(text=request.prompt, provider="fake")

    result = FakeProvider().generate(GenerationRequest(prompt="Hello"))

    assert result == GenerationResult(text="Hello", provider="fake")
