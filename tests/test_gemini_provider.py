"""Testes unitários dos requisitos do provider Gemini, sem chamadas reais."""

from unittest.mock import Mock, patch

import pytest

from src.core.interfaces import AIProvider, GenerationRequest, GenerationResult
from src.providers.gemini_provider import GeminiProvider


@patch("src.providers.gemini_provider.genai.Client")
def test_gemini_provider_uses_api_key_and_default_model(mock_client):
    """Requisito: usar a chave de ambiente, o modelo padrão e o prompt recebido.

    Resultado esperado: o provider implementa ``AIProvider``, inicializa o
    cliente com a chave e devolve exatamente o texto produzido pelo mock da API.
    """
    mock_response = Mock(
        text="Generated response",
        model_version=None,
        response_id=None,
        usage_metadata=None,
    )
    mock_client.return_value.models.generate_content.return_value = mock_response

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        provider = GeminiProvider()
        result = provider.generate(GenerationRequest(prompt="Test prompt"))

    assert isinstance(provider, AIProvider)
    mock_client.assert_called_once_with(api_key="test-key")
    mock_client.return_value.models.generate_content.assert_called_once_with(
        model="gemini-3.1-flash-lite",
        contents="Test prompt",
    )
    assert isinstance(result, GenerationResult)
    assert result.text == "Generated response"
    assert result.provider == "gemini"
    assert result.requested_model == "gemini-3.1-flash-lite"
    assert result.actual_model == "gemini-3.1-flash-lite"


@patch("src.providers.gemini_provider.genai.Client")
def test_generate_maps_all_supported_request_fields(mock_client):
    """Requisito: mapear os parâmetros validados pelo notebook Gemini."""
    mock_response = Mock(
        text='  {"ok": true}  ',
        model_version="gemini-reported-version",
        response_id="response-123",
        usage_metadata={"prompt_token_count": 10, "total_token_count": 15},
    )
    mock_client.return_value.models.generate_content.return_value = mock_response

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        provider = GeminiProvider()

    result = provider.generate(
        GenerationRequest(
            prompt="Test prompt",
            system_prompt="Return JSON",
            model="gemini-override",
            temperature=0.8,
            max_tokens=4000,
            require_json=True,
        )
    )

    call = mock_client.return_value.models.generate_content.call_args
    assert call.kwargs["model"] == "gemini-override"
    assert call.kwargs["contents"] == "Test prompt"
    assert call.kwargs["config"].system_instruction == "Return JSON"
    assert call.kwargs["config"].temperature == 0.8
    assert call.kwargs["config"].max_output_tokens == 4000
    assert call.kwargs["config"].response_mime_type == "application/json"
    assert result.text == '{"ok": true}'
    assert result.requested_model == "gemini-override"
    assert result.actual_model == "gemini-reported-version"
    assert result.usage == {
        "prompt_token_count": 10,
        "total_token_count": 15,
    }
    assert result.metadata == {"response_id": "response-123"}
    assert result.attempts == [
        {"model": "gemini-override", "attempt": 1, "success": True}
    ]


@patch("src.providers.gemini_provider.genai.Client")
def test_missing_api_key_raises_clear_error(mock_client):
    """Requisito: a variável ``GEMINI_API_KEY`` é obrigatória.

    Resultado esperado: a construção lança ``ValueError`` com o nome da variável
    e o cliente Gemini não chega a ser instanciado.
    """
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            GeminiProvider()

    mock_client.assert_not_called()


@patch("src.providers.gemini_provider.genai.Client")
def test_generate_returns_string_when_response_text_is_empty(mock_client):
    """Requisito: ``generate`` deve devolver sempre uma string.

    Resultado esperado: quando o SDK não disponibiliza texto, o provider
    normaliza o valor ``None`` para uma string vazia.
    """
    mock_response = Mock(
        text=None,
        model_version=None,
        response_id=None,
        usage_metadata=None,
    )
    mock_client.return_value.models.generate_content.return_value = mock_response

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        result = GeminiProvider().generate(
            GenerationRequest(prompt="Test prompt")
        )

    assert result.text == ""
    assert isinstance(result.text, str)
