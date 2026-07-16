"""Testes do provider manual através do contrato comum."""

import pytest

from src.core.interfaces import AIProvider, GenerationRequest, GenerationResult
from src.providers.manual_provider import ManualProvider


def test_manual_provider_returns_constructor_response(capsys, tmp_path):
    """Uma resposta fornecida ao provider evita leitura interativa."""
    prompt_path = tmp_path / "manual-prompt.txt"
    provider = ManualProvider(prompt_path=prompt_path, response="Manual answer")
    request = GenerationRequest(
        prompt="User instruction",
        system_prompt="System instruction",
        model_candidates=["preferred-model", "fallback-model"],
        require_json=True,
    )

    result = provider.generate(request)

    assert isinstance(provider, AIProvider)
    assert isinstance(result, GenerationResult)
    assert result.text == "Manual answer"
    assert result.provider == "manual"
    assert result.requested_model == "preferred-model"
    assert result.actual_model is None
    assert result.metadata == {"response_mode": "provided"}
    assert result.attempts == [
        {"model": "preferred-model", "attempt": 1, "success": True}
    ]
    assert prompt_path.read_text(encoding="utf-8") == (
        "--- System prompt ---\n"
        "System instruction\n\n"
        "--- User prompt ---\n"
        "User instruction"
    )
    assert "System instruction" in capsys.readouterr().out


def test_manual_provider_uses_injected_response_source():
    """A origem injetada permite respostas manuais sem alterar o pedido."""
    provider = ManualProvider(response_source=lambda: "Injected answer")

    result = provider.generate(GenerationRequest(prompt="Prompt", model="model-a"))

    assert result.text == "Injected answer"
    assert result.requested_model == "model-a"
    assert result.metadata == {"response_mode": "injected"}


def test_manual_provider_rejects_two_response_sources():
    """A origem da resposta manual deve ser inequívoca."""
    with pytest.raises(ValueError, match="either response or response_source"):
        ManualProvider(response="Answer", response_source=lambda: "Other")
