"""Testes unitários do provider OpenRouter com HTTP e espera simulados."""

from unittest.mock import Mock, patch

import pytest

from src.core.interfaces import GenerationRequest
from src.providers.openrouter_provider import OpenRouterProvider


def _response(
    status: int,
    data: dict | None = None,
    headers: dict[str, str] | None = None,
) -> Mock:
    """Cria uma resposta HTTP mínima para os cenários de fallback."""
    response = Mock(
        status_code=status,
        ok=200 <= status < 300,
        headers=headers or {},
    )
    response.json.return_value = data or {}
    return response


@patch("src.providers.openrouter_provider.requests.post")
@patch("src.providers.openrouter_provider.requests.get")
def test_openrouter_first_available_candidate_succeeds(mock_get, mock_post):
    """Requisito: filtrar disponibilidade sem alterar a ordem dos candidatos.

    Resultado esperado: o primeiro candidato configurado disponível recebe o
    payload completo e o resultado distingue modelos pedido e reportado.
    """
    mock_get.return_value = _response(
        200,
        {
            "data": [
                {"id": "candidate-b"},
                {"id": "candidate-a"},
                {"id": "unrelated"},
            ]
        },
    )
    mock_post.return_value = _response(
        200,
        {
            "model": "routed-model",
            "choices": [{"message": {"content": " Generated "}}],
            "usage": {"prompt_tokens": 4, "total_tokens": 9},
        },
    )

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "router-key"}):
        provider = OpenRouterProvider()
        result = provider.generate(
            GenerationRequest(
                prompt="User",
                system_prompt="System",
                model_candidates=["candidate-a", "candidate-b"],
                temperature=0.8,
                max_tokens=4000,
                require_json=True,
            )
        )

    headers = {
        "Authorization": "Bearer router-key",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://colab.research.google.com",
        "X-Title": "Cognitive Curriculum Provider Validation",
    }
    mock_get.assert_called_once_with(
        "https://openrouter.ai/api/v1/models",
        headers=headers,
        timeout=60,
    )
    mock_post.assert_called_once_with(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json={
            "model": "candidate-a",
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
    assert result.requested_model == "candidate-a"
    assert result.actual_model == "routed-model"
    assert result.usage == {"prompt_tokens": 4, "total_tokens": 9}
    assert result.metadata["candidate_models"] == ["candidate-a", "candidate-b"]
    assert result.attempts == [
        {
            "model": "candidate-a",
            "attempt": 1,
            "success": True,
            "status_code": 200,
        }
    ]


@patch("src.providers.openrouter_provider.requests.post")
@patch("src.providers.openrouter_provider.requests.get")
def test_openrouter_explicit_model_is_the_only_candidate(mock_get, mock_post):
    """Requisito: request.model deve limitar a execução a esse modelo.

    Resultado esperado: apenas o modelo explícito é publicado no POST e metadata.
    """
    mock_get.return_value = _response(
        200,
        {"data": [{"id": "explicit"}, {"id": "other"}]},
    )
    mock_post.return_value = _response(
        200,
        {"choices": [{"message": {"content": "ok"}}]},
    )

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "key"}):
        result = OpenRouterProvider().generate(
            GenerationRequest(prompt="Prompt", model="explicit")
        )

    assert mock_post.call_args.kwargs["json"]["model"] == "explicit"
    assert result.metadata["candidate_models"] == ["explicit"]


@pytest.mark.parametrize(
    ("headers", "error_data", "expected_delay"),
    [
        ({"Retry-After": "7"}, {}, 7),
        ({}, {"error": {"metadata": {"retry_after_seconds": 5}}}, 5),
        ({}, {"error": {}}, 12),
    ],
)
@patch("src.providers.openrouter_provider.time.sleep")
@patch("src.providers.openrouter_provider.requests.post")
@patch("src.providers.openrouter_provider.requests.get")
def test_openrouter_retry_delay_sources(
    mock_get,
    mock_post,
    mock_sleep,
    headers,
    error_data,
    expected_delay,
):
    """Requisito: retry deve priorizar cabeçalho, metadata e valor padrão.

    Resultado esperado: cada fonte produz uma espera simulada de delay mais um.
    """
    mock_get.return_value = _response(200, {"data": [{"id": "model-a"}]})
    mock_post.side_effect = [
        _response(429, error_data, headers),
        _response(200, {"choices": [{"message": {"content": "ok"}}]}),
    ]

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "key"}):
        result = OpenRouterProvider().generate(
            GenerationRequest(prompt="Prompt", model="model-a")
        )

    mock_sleep.assert_called_once_with(expected_delay + 1)
    assert result.attempts[0]["retry_after_seconds"] == expected_delay
    assert len(result.attempts) == 2


@patch("src.providers.openrouter_provider.time.sleep")
@patch("src.providers.openrouter_provider.requests.post")
@patch("src.providers.openrouter_provider.requests.get")
def test_openrouter_two_failures_then_next_model(
    mock_get,
    mock_post,
    mock_sleep,
):
    """Requisito: duas falhas retryable devem avançar para o candidato seguinte.

    Resultado esperado: o histórico conserva duas falhas e o sucesso seguinte.
    """
    mock_get.return_value = _response(
        200,
        {"data": [{"id": "model-a"}, {"id": "model-b"}]},
    )
    mock_post.side_effect = [
        _response(429, {}, {"Retry-After": "2"}),
        _response(429),
        _response(
            200,
            {
                "model": "actual-b",
                "choices": [{"message": {"content": "success"}}],
            },
        ),
    ]

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "key"}):
        result = OpenRouterProvider().generate(
            GenerationRequest(
                prompt="Prompt",
                model_candidates=["model-a", "model-b"],
            )
        )

    assert [call.kwargs["json"]["model"] for call in mock_post.call_args_list] == [
        "model-a",
        "model-a",
        "model-b",
    ]
    mock_sleep.assert_called_once_with(3)
    assert result.requested_model == "model-b"
    assert result.actual_model == "actual-b"
    assert [attempt["success"] for attempt in result.attempts] == [
        False,
        False,
        True,
    ]


@patch("src.providers.openrouter_provider.time.sleep")
@patch("src.providers.openrouter_provider.requests.post")
@patch("src.providers.openrouter_provider.requests.get")
def test_openrouter_non_retryable_error_moves_immediately(
    mock_get,
    mock_post,
    mock_sleep,
):
    """Requisito: erro não retryable deve avançar sem nova tentativa nem espera.

    Resultado esperado: o segundo modelo é chamado imediatamente e tem sucesso.
    """
    mock_get.return_value = _response(
        200,
        {"data": [{"id": "model-a"}, {"id": "model-b"}]},
    )
    mock_post.side_effect = [
        _response(404),
        _response(200, {"choices": [{"message": {"content": "ok"}}]}),
    ]

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "key"}):
        result = OpenRouterProvider().generate(
            GenerationRequest(
                prompt="Prompt",
                model_candidates=["model-a", "model-b"],
            )
        )

    mock_sleep.assert_not_called()
    assert result.requested_model == "model-b"
    assert len(result.attempts) == 2


@patch("src.providers.openrouter_provider.time.sleep")
@patch("src.providers.openrouter_provider.requests.post")
@patch("src.providers.openrouter_provider.requests.get")
def test_openrouter_all_candidates_failing_raises_clear_error(
    mock_get,
    mock_post,
    mock_sleep,
):
    """Requisito: falha de todos os candidatos deve terminar claramente.

    Resultado esperado: RuntimeError resume modelos e estados sem expor secrets.
    """
    mock_get.return_value = _response(200, {"data": [{"id": "model-a"}]})
    mock_post.side_effect = [_response(503), _response(503)]

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "secret-key"}):
        with pytest.raises(RuntimeError, match="model-a:503") as error:
            OpenRouterProvider().generate(
                GenerationRequest(prompt="Prompt", model="model-a")
            )

    assert "secret-key" not in str(error.value)
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(13)


@patch("src.providers.openrouter_provider.requests.get")
def test_openrouter_missing_key_raises_clear_error(mock_get):
    """Requisito: OPENROUTER_API_KEY é obrigatória.

    Resultado esperado: ValueError identifica a variável e nenhum HTTP ocorre.
    """
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            OpenRouterProvider()

    mock_get.assert_not_called()
