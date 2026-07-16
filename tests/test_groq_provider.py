"""Testes unitários do provider Groq sem chamadas reais."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from src.core.interfaces import AIProvider, GenerationRequest, GenerationResult
from src.providers.groq_provider import GroqProvider


def _completion(
    text: str = " Generated response ",
    model: str = "reported-model",
) -> SimpleNamespace:
    """Cria uma completion Groq mínima para testes."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        model=model,
        usage={"prompt_tokens": 10, "completion_tokens": 5},
    )


@patch("src.providers.groq_provider.Groq")
def test_groq_complete_notebook_compatible_request(mock_client):
    """Requisito: preservar descoberta, seleção e payload do notebook Groq.

    Resultado esperado: o primeiro candidato disponível é usado com todos os
    parâmetros e o resultado contém texto, modelos, utilização e tentativa.
    """
    client = mock_client.return_value
    client.models.list.return_value.data = [
        SimpleNamespace(id="openai/gpt-oss-120b"),
        SimpleNamespace(id="llama-3.3-70b-versatile"),
    ]
    client.chat.completions.create.return_value = _completion()

    with patch.dict("os.environ", {"GROQ_API_KEY": "groq-key"}):
        provider = GroqProvider()
        result = provider.generate(
            GenerationRequest(
                prompt="User prompt",
                system_prompt="System prompt",
                temperature=0.8,
                max_tokens=4000,
                require_json=True,
            )
        )

    assert isinstance(provider, AIProvider)
    assert isinstance(result, GenerationResult)
    mock_client.assert_called_once_with(api_key="groq-key")
    client.models.list.assert_called_once_with()
    client.chat.completions.create.assert_called_once_with(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User prompt"},
        ],
        temperature=0.8,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    assert result.text == "Generated response"
    assert result.provider == "groq"
    assert result.requested_model == "llama-3.3-70b-versatile"
    assert result.actual_model == "reported-model"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5}
    assert result.attempts == [
        {"model": "llama-3.3-70b-versatile", "attempt": 1, "success": True}
    ]


@patch("src.providers.groq_provider.Groq")
def test_groq_explicit_model_is_used_directly(mock_client):
    """Requisito: request.model deve prevalecer sobre a descoberta.

    Resultado esperado: o modelo explícito é enviado mesmo sem constar na lista
    descoberta e não ocorre qualquer fallback após a completion.
    """
    client = mock_client.return_value
    client.models.list.return_value.data = [SimpleNamespace(id="other-model")]
    client.chat.completions.create.return_value = _completion(model="explicit")

    with patch.dict("os.environ", {"GROQ_API_KEY": "key"}):
        result = GroqProvider().generate(
            GenerationRequest(prompt="Prompt", model="explicit")
        )

    assert client.chat.completions.create.call_args.kwargs["model"] == "explicit"
    assert result.requested_model == "explicit"


@patch("src.providers.groq_provider.Groq")
def test_groq_request_candidates_override_defaults(mock_client):
    """Requisito: candidatos do pedido devem substituir a lista padrão.

    Resultado esperado: a ordem do pedido é respeitada entre modelos disponíveis.
    """
    client = mock_client.return_value
    client.models.list.return_value.data = [
        SimpleNamespace(id="candidate-b"),
        SimpleNamespace(id="candidate-a"),
    ]
    client.chat.completions.create.return_value = _completion()

    with patch.dict("os.environ", {"GROQ_API_KEY": "key"}):
        result = GroqProvider().generate(
            GenerationRequest(
                prompt="Prompt",
                model_candidates=["candidate-a", "candidate-b"],
            )
        )

    assert result.requested_model == "candidate-a"


@patch("src.providers.groq_provider.Groq")
def test_groq_raises_when_no_candidate_is_available(mock_client):
    """Requisito: ausência de candidatos disponíveis deve ser explícita.

    Resultado esperado: é lançado RuntimeError antes de criar uma completion.
    """
    client = mock_client.return_value
    client.models.list.return_value.data = [SimpleNamespace(id="unrelated")]

    with patch.dict("os.environ", {"GROQ_API_KEY": "key"}):
        with pytest.raises(RuntimeError, match="Groq model candidate"):
            GroqProvider().generate(GenerationRequest(prompt="Prompt"))

    client.chat.completions.create.assert_not_called()


@patch("src.providers.groq_provider.Groq")
def test_groq_missing_key_raises_clear_error(mock_client):
    """Requisito: GROQ_API_KEY é obrigatória.

    Resultado esperado: ValueError identifica a variável e o SDK não é criado.
    """
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            GroqProvider()

    mock_client.assert_not_called()
