"""Implementa um provider interativo para fluxos manuais de copy/paste."""

from pathlib import Path

from src.core.interfaces import AIProvider


class ManualProvider(AIProvider):
    """Permite obter respostas através de interação manual com qualquer modelo.

    O objetivo é mostrar e, opcionalmente, guardar o prompt para o utilizador o
    enviar a um modelo externo. O output é uma resposta fornecida diretamente
    ou o texto introduzido pelo utilizador na consola.
    """

    def __init__(self, prompt_path: str | Path | None = None) -> None:
        """Configura o caminho opcional onde cada prompt será guardado."""
        self.prompt_path = Path(prompt_path) if prompt_path else None

    def generate(self, prompt: str, response: str | None = None) -> str:
        """Apresenta e guarda o prompt, devolvendo uma resposta textual.

        Se ``response`` for fornecida, é devolvida sem pedir input. Caso
        contrário, o método lê a resposta multilinha introduzida na consola.
        """

        self._show_prompt(prompt)
        self._save_prompt(prompt)

        if response is not None:
            return response

        return self._read_response()

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
