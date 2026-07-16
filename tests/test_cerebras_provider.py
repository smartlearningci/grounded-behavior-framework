"""Testes unitários do provider Cerebras com HTTP e espera simulados."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.core.interfaces import GenerationRequest
from src.providers.cerebras_provider import CerebrasProvider


def _response(
    status: int,
    data: dict | None = None,
    headers: dict[str, str] | None = None,
) -> Mock:
    """Cria uma resposta HTTP mínima para seleção e retry."""
    response = Mock(
        status_code=status,
        ok=200 <= status < 300,
        headers=headers or {},
    )
    response.json.return_value = data or {}
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(str(status))
    return response


@patch("src.providers.cerebras_provider.requests.post")
@patch("src.providers.cerebras_provider.requests.get")
def test_cerebras_complete_notebook_compatible_request(mock_get, mock_post):
    """Requisito: preservar seleção, mensagens e geração do notebook Cerebras.

    Resultado esperado: o candidato prioritário recebe todas as opções e o
    resultado conserva texto, modelo reportado, utilização e tentativa.
    """
    mock_get.return_value = _response(
        200,
        {"data": [{"id": "zai-glm-4.7"}, {"id": "gemma-4-31b"}]},
    )
    mock_post.return_value = _response(
        200,
        {
            "model": "gemma-actual",
            "choices": [{"message": {"content": " Generated "}}],
            "usage": {"prompt_tokens": 7, "total_tokens": 11},
        },
    )

    with patch.dict("os.environ", {"CEREBRAS_API_KEY": "cerebras-key"}):
        result = CerebrasProvider().generate(
            GenerationRequest(
                prompt="User",
                system_prompt="System",
                temperature=0.8,
                max_tokens=4000,
                require_json=True,
            )
        )

    headers = {
        "Authorization": "Bearer cerebras-key",
        "Content-Type": "application/json",
    }
    mock_get.assert_called_once_with(
        "https://api.cerebras.ai/v1/models",
        headers=headers,
        timeout=60,
    )
    mock_post.assert_called_once_with(
        "https://api.cerebras.ai/v1/chat/completions",
        headers=headers,
        json={
            "model": "gemma-4-31b",
            "messages": [
                {"role": "system", "content": "System"},
                {"role": "user", "content": "User"},
            ],
            "temperature": 0.8,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"},
        },
        timeout=180,
    )
    assert result.text == "Generated"
    assert result.requested_model == "gemma-4-31b"
    assert result.actual_model == "gemma-actual"
    assert result.usage == {"prompt_tokens": 7, "total_tokens": 11}
    assert result.metadata["model_selection"] == "candidate"
    assert result.attempts[-1]["success"] is True


@patch("src.providers.cerebras_provider.requests.post")
@patch("src.providers.cerebras_provider.requests.get")
def test_cerebras_request_candidates_override_defaults(mock_get, mock_post):
    """Requisito: candidatos do pedido devem substituir os candidatos padrão.

    Resultado esperado: o primeiro candidato do pedido disponível é selecionado.
    """
    mock_get.return_value = _response(
        200,
        {"data": [{"id": "candidate-b"}, {"id": "candidate-a"}]},
    )
    mock_post.return_value = _response(
        200,
        {"choices": [{"message": {"content": "ok"}}]},
    )

    with patch.dict("os.environ", {"CEREBRAS_API_KEY": "key"}):
        result = CerebrasProvider().generate(
            GenerationRequest(
                prompt="Prompt",
                model_candidates=["candidate-a", "candidate-b"],
            )
        )

    assert result.requested_model == "candidate-a"


@patch("src.providers.cerebras_provider.requests.post")
@patch("src.providers.cerebras_provider.requests.get")
def test_cerebras_explicit_model_is_used_directly(mock_get, mock_post):
    """Requisito: request.model deve prevalecer sobre descoberta e candidatos.

    Resultado esperado: o modelo explícito é usado sem substituição textual.
    """
    mock_get.return_value = _response(200, {"data": [{"id": "other"}]})
    mock_post.return_value = _response(
        200,
        {"choices": [{"message": {"content": "ok"}}]},
    )

    with patch.dict("os.environ", {"CEREBRAS_API_KEY": "key"}):
        result = CerebrasProvider().generate(
            GenerationRequest(prompt="Prompt", model="explicit")
        )

    assert result.requested_model == "explicit"
    assert result.metadata["model_selection"] == "explicit"


@patch("src.providers.cerebras_provider.requests.post")
@patch("src.providers.cerebras_provider.requests.get")
def test_cerebras_uses_first_non_excluded_textual_model(mock_get, mock_post):
    """Requisito: ausência de candidatos deve ativar o fallback textual.

    Resultado esperado: termos excluídos são ignorados e o primeiro textual é usado.
    """
    mock_get.return_value = _response(
        200,
        {
            "data": [
                {"id": "alpha-embed-model"},
                {"id": "beta-guard-model"},
                {"id": "zeta-text-model"},
            ]
        },
    )
    mock_post.return_value = _response(
        200,
        {"choices": [{"message": {"content": "ok"}}]},
    )

    with patch.dict("os.environ", {"CEREBRAS_API_KEY": "key"}):
        result = CerebrasProvider().generate(GenerationRequest(prompt="Prompt"))

    assert result.requested_model == "zeta-text-model"
    assert result.metadata["model_selection"] == "textual_fallback"


@patch("src.providers.cerebras_provider.requests.post")
@patch("src.providers.cerebras_provider.requests.get")
def test_cerebras_raises_when_no_textual_model_exists(mock_get, mock_post):
    """Requisito: o fallback deve rejeitar inventários apenas não textuais.

    Resultado esperado: RuntimeError é lançado antes de qualquer geração HTTP.
    """
    mock_get.return_value = _response(
        200,
        {
            "data": [
                {"id": "embed-model"},
                {"id": "rerank-model"},
                {"id": "guard-model"},
                {"id": "safety-model"},
                {"id": "moderation-model"},
                {"id": "ocr-model"},
                {"id": "audio-model"},
                {"id": "image-model"},
            ]
        },
    )

    with patch.dict("os.environ", {"CEREBRAS_API_KEY": "key"}):
        with pytest.raises(RuntimeError, match="textual Cerebras model"):
            CerebrasProvider().generate(GenerationRequest(prompt="Prompt"))

    mock_post.assert_not_called()


@patch("src.providers.cerebras_provider.time.sleep")
@patch("src.providers.cerebras_provider.requests.post")
@patch("src.providers.cerebras_provider.requests.get")
def test_cerebras_retries_same_model_with_retry_after(
    mock_get,
    mock_post,
    mock_sleep,
):
    """Requisito: erros transitórios repetem o mesmo modelo até três vezes.

    Resultado esperado: Retry-After é honrado, não há fallback e todas as
    tentativas ficam registadas antes do sucesso da terceira chamada.
    """
    mock_get.return_value = _response(
        200,
        {"data": [{"id": "gemma-4-31b"}, {"id": "zai-glm-4.7"}]},
    )
    mock_post.side_effect = [
        _response(429, headers={"Retry-After": "3"}),
        _response(503),
        _response(
            200,
            {"choices": [{"message": {"content": "success"}}]},
        ),
    ]

    with patch.dict("os.environ", {"CEREBRAS_API_KEY": "key"}):
        result = CerebrasProvider().generate(GenerationRequest(prompt="Prompt"))

    assert [call.kwargs["json"]["model"] for call in mock_post.call_args_list] == [
        "gemma-4-31b",
        "gemma-4-31b",
        "gemma-4-31b",
    ]
    assert mock_sleep.call_args_list[0].args == (4,)
    assert mock_sleep.call_args_list[1].args == (11,)
    assert len(result.attempts) == 3


@patch("src.providers.cerebras_provider.time.sleep")
@patch("src.providers.cerebras_provider.requests.post")
@patch("src.providers.cerebras_provider.requests.get")
def test_cerebras_stops_after_three_failed_attempts(
    mock_get,
    mock_post,
    mock_sleep,
):
    """Requisito: o máximo é três tentativas sem mudar de candidato.

    Resultado esperado: o terceiro erro HTTP é propagado após duas esperas reais
    substituídas por mocks e nenhum segundo modelo é chamado.
    """
    mock_get.return_value = _response(
        200,
        {"data": [{"id": "gemma-4-31b"}, {"id": "zai-glm-4.7"}]},
    )
    mock_post.side_effect = [_response(503), _response(503), _response(503)]

    with patch.dict("os.environ", {"CEREBRAS_API_KEY": "key"}):
        with pytest.raises(requests.HTTPError):
            CerebrasProvider().generate(GenerationRequest(prompt="Prompt"))

    assert mock_post.call_count == 3
    assert all(
        call.kwargs["json"]["model"] == "gemma-4-31b"
        for call in mock_post.call_args_list
    )
    assert mock_sleep.call_count == 2


@patch("src.providers.cerebras_provider.requests.get")
def test_cerebras_missing_key_raises_clear_error(mock_get):
    """Requisito: CEREBRAS_API_KEY é obrigatória.

    Resultado esperado: ValueError identifica a variável e nenhum HTTP ocorre.
    """
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="CEREBRAS_API_KEY"):
            CerebrasProvider()

    mock_get.assert_not_called()
