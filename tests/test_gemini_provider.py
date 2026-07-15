"""Testes unitários dos requisitos do provider Gemini, sem chamadas reais."""

from unittest.mock import Mock, patch

import pytest

from src.core.interfaces import AIProvider
from src.providers.gemini_provider import GeminiProvider


@patch("src.providers.gemini_provider.genai.Client")
def test_gemini_provider_uses_api_key_and_default_model(mock_client):
    """Requisito: usar a chave de ambiente, o modelo padrão e o prompt recebido.

    Resultado esperado: o provider implementa ``AIProvider``, inicializa o
    cliente com a chave e devolve exatamente o texto produzido pelo mock da API.
    """
    mock_client.return_value.models.generate_content.return_value.text = (
        "Generated response"
    )

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        provider = GeminiProvider()
        result = provider.generate("Test prompt")

    assert isinstance(provider, AIProvider)
    mock_client.assert_called_once_with(api_key="test-key")
    mock_client.return_value.models.generate_content.assert_called_once_with(
        model="gemini-3.1-flash-lite",
        contents="Test prompt",
    )
    assert result == "Generated response"


@patch("src.providers.gemini_provider.genai.Client")
def test_generate_returns_provided_response_without_calling_api(mock_client):
    """Requisito: uma resposta fornecida deve ser devolvida imediatamente.

    Resultado esperado: o texto fornecido é devolvido sem executar o método
    ``generate_content`` do cliente Gemini simulado.
    """
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        provider = GeminiProvider()

    result = provider.generate("Test prompt", response="Provided response")

    assert result == "Provided response"
    mock_client.return_value.models.generate_content.assert_not_called()


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
    mock_response = Mock()
    mock_response.text = None
    mock_client.return_value.models.generate_content.return_value = mock_response

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        result = GeminiProvider().generate("Test prompt")

    assert result == ""
    assert isinstance(result, str)
