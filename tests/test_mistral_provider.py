"""Testes unitários do provider Mistral com HTTP simulado."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.core.interfaces import GenerationRequest
from src.providers.mistral_provider import MistralProvider


def _http_response(status: int, data: dict) -> Mock:
    """Cria uma resposta HTTP mínima e configurável."""
    response = Mock(status_code=status, ok=200 <= status < 300)
    response.json.return_value = data
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(str(status))
    return response


@patch("src.providers.mistral_provider.requests.post")
@patch("src.providers.mistral_provider.requests.get")
def test_mistral_complete_notebook_compatible_request(mock_get, mock_post):
    """Requisito: preservar endpoints, seleção, mensagens e opções Mistral.

    Resultado esperado: GET e POST usam cabeçalhos e timeouts validados e o
    resultado conserva texto, modelo real, utilização e tentativa.
    """
    mock_get.return_value = _http_response(
        200,
        {"data": [{"id": "mistral-small-2603"}, {"id": "mistral-small-latest"}]},
    )
    mock_post.return_value = _http_response(
        200,
        {
            "model": "mistral-actual",
            "choices": [{"message": {"content": " Generated "}}],
            "usage": {"prompt_tokens": 8, "total_tokens": 12},
        },
    )

    with patch.dict("os.environ", {"MISTRAL_API_KEY": "mistral-key"}):
        result = MistralProvider().generate(
            GenerationRequest(
                prompt="User",
                system_prompt="System",
                temperature=0.8,
                max_tokens=4000,
                require_json=True,
            )
        )

    headers = {
        "Authorization": "Bearer mistral-key",
        "Content-Type": "application/json",
    }
    mock_get.assert_called_once_with(
        "https://api.mistral.ai/v1/models",
        headers=headers,
        timeout=60,
    )
    mock_post.assert_called_once_with(
        "https://api.mistral.ai/v1/chat/completions",
        headers=headers,
        json={
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": "System"},
                {"role": "user", "content": "User"},
            ],
            "temperature": 0.8,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"},
        },
        timeout=120,
    )
    assert result.text == "Generated"
    assert result.requested_model == "mistral-small-latest"
    assert result.actual_model == "mistral-actual"
    assert result.usage == {"prompt_tokens": 8, "total_tokens": 12}


@patch("src.providers.mistral_provider.requests.post")
@patch("src.providers.mistral_provider.requests.get")
def test_mistral_explicit_model_overrides_selection(mock_get, mock_post):
    """Requisito: um modelo explícito deve ser usado diretamente.

    Resultado esperado: o POST usa request.model apesar da lista descoberta.
    """
    mock_get.return_value = _http_response(200, {"data": [{"id": "other"}]})
    mock_post.return_value = _http_response(
        200,
        {"choices": [{"message": {"content": "ok"}}]},
    )

    with patch.dict("os.environ", {"MISTRAL_API_KEY": "key"}):
        result = MistralProvider().generate(
            GenerationRequest(prompt="Prompt", model="explicit")
        )

    assert mock_post.call_args.kwargs["json"]["model"] == "explicit"
    assert result.requested_model == "explicit"


@patch("src.providers.mistral_provider.requests.post")
@patch("src.providers.mistral_provider.requests.get")
def test_mistral_request_candidates_and_http_error(mock_get, mock_post):
    """Requisito: candidatos do pedido têm prioridade e erros HTTP propagam.

    Resultado esperado: o primeiro candidato disponível é enviado e o erro do
    POST é novamente lançado sem retry nem fallback.
    """
    mock_get.return_value = _http_response(
        200,
        {"data": [{"id": "candidate-b"}, {"id": "candidate-a"}]},
    )
    mock_post.return_value = _http_response(503, {"error": {}})

    with patch.dict("os.environ", {"MISTRAL_API_KEY": "key"}):
        with pytest.raises(requests.HTTPError):
            MistralProvider().generate(
                GenerationRequest(
                    prompt="Prompt",
                    model_candidates=["candidate-a", "candidate-b"],
                )
            )

    assert mock_post.call_args.kwargs["json"]["model"] == "candidate-a"
    assert mock_post.call_count == 1


@patch("src.providers.mistral_provider.requests.post")
@patch("src.providers.mistral_provider.requests.get")
def test_mistral_raises_when_no_candidate_is_available(mock_get, mock_post):
    """Requisito: a seleção deve falhar quando nenhum candidato está disponível.

    Resultado esperado: RuntimeError ocorre antes do endpoint de geração.
    """
    mock_get.return_value = _http_response(
        200,
        {"data": [{"id": "unrelated-model"}]},
    )

    with patch.dict("os.environ", {"MISTRAL_API_KEY": "key"}):
        with pytest.raises(RuntimeError, match="Mistral model candidate"):
            MistralProvider().generate(GenerationRequest(prompt="Prompt"))

    mock_post.assert_not_called()


@patch("src.providers.mistral_provider.requests.get")
def test_mistral_missing_key_raises_clear_error(mock_get):
    """Requisito: MISTRAL_API_KEY é obrigatória.

    Resultado esperado: ValueError identifica a variável e nenhum HTTP ocorre.
    """
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="MISTRAL_API_KEY"):
            MistralProvider()

    mock_get.assert_not_called()
