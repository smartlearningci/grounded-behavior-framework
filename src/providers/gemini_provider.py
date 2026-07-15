"""Implementa a geração de texto através da API oficial Google Gemini."""

import os

from google import genai

from src.core.interfaces import AIProvider


class GeminiProvider(AIProvider):
    """Adapta o cliente Gemini ao contrato comum ``AIProvider``.

    O objetivo é enviar prompts textuais ao modelo configurado usando a chave
    ``GEMINI_API_KEY``. O output de ``generate`` é sempre uma string com a
    resposta fornecida pelo chamador ou o texto gerado pela API.
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

    def generate(self, prompt: str, response: str | None = None) -> str:
        """Devolve uma resposta existente ou gera texto para ``prompt``.

        Uma ``response`` fornecida tem prioridade e evita a chamada à API. Sem
        ela, envia o prompt ao Gemini e devolve o texto gerado; texto ausente é
        normalizado para uma string vazia.
        """
        if response is not None:
            return response

        generated = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return generated.text or ""
