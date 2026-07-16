"""Implementa um provider interativo para fluxos manuais de copy/paste."""

from pathlib import Path
from typing import Callable

from src.core.interfaces import (
    AIProvider,
    GenerationRequest,
    GenerationResult,
)


class ManualProvider(AIProvider):
    """Permite obter respostas através de interação manual com qualquer modelo.

    O objetivo é mostrar e, opcionalmente, guardar o prompt para o utilizador o
    enviar a um modelo externo. A resposta pode vir do construtor, de uma origem
    injetada ou do texto introduzido pelo utilizador na consola.
    """

    def __init__(
        self,
        prompt_path: str | Path | None = None,
        response: str | None = None,
        response_source: Callable[[], str] | None = None,
    ) -> None:
        """Configura a persistência e a origem opcional da resposta manual."""
        if response is not None and response_source is not None:
            raise ValueError("Provide either response or response_source, not both")

        self.prompt_path = Path(prompt_path) if prompt_path else None
        self.response = response
        self.response_source = response_source

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Apresenta o pedido e devolve a resposta obtida manualmente."""
        prompt = self._format_prompt(request)

        self._show_prompt(prompt)
        self._save_prompt(prompt)

        if self.response is not None:
            text = self.response
            response_mode = "provided"
        elif self.response_source is not None:
            text = self.response_source()
            response_mode = "injected"
        else:
            text = self._read_response()
            response_mode = "console"

        requested_model = request.model
        if requested_model is None and request.model_candidates:
            requested_model = request.model_candidates[0]

        return GenerationResult(
            text=text,
            provider="manual",
            requested_model=requested_model,
            actual_model=None,
            metadata={"response_mode": response_mode},
            attempts=[
                {
                    "model": requested_model,
                    "attempt": 1,
                    "success": True,
                }
            ],
        )

    def _format_prompt(self, request: GenerationRequest) -> str:
        """Representa separadamente as instruções de sistema e do utilizador."""
        if request.system_prompt is None:
            return request.prompt

        return (
            "--- System prompt ---\n"
            f"{request.system_prompt}\n\n"
            "--- User prompt ---\n"
            f"{request.prompt}"
        )

    def _show_prompt(self, prompt: str) -> None:
        """Mostra o prompt na consola entre delimitadores visuais."""
        print("\n--- Prompt to paste into a chat model ---\n")
        print(prompt)
        print("\n--- End prompt ---\n")

    def _save_prompt(self, prompt: str) -> None:
        """Guarda o prompt em UTF-8 quando foi configurado um caminho."""
        if self.prompt_path is None:
            return

        self.prompt_path.parent.mkdir(parents=True, exist_ok=True)
        self.prompt_path.write_text(prompt, encoding="utf-8")

    def _read_response(self) -> str:
        """Lê linhas da consola até EOF e devolve a resposta sem margens."""
        print("Paste the model response below. Press Ctrl-D when finished:\n")

        lines: list[str] = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            return "\n".join(lines).strip()
