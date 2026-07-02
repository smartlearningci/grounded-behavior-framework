from pathlib import Path

from src.core.interfaces import AIProvider


class ManualProvider(AIProvider):
    """Manual provider for copy/paste workflows with any chat model."""

    def __init__(self, prompt_path: str | Path | None = None) -> None:
        self.prompt_path = Path(prompt_path) if prompt_path else None

    def generate(self, prompt: str, response: str | None = None) -> str:
        """Print/save a prompt and return a manually pasted response."""

        self._show_prompt(prompt)
        self._save_prompt(prompt)

        if response is not None:
            return response

        return self._read_response()

    def _show_prompt(self, prompt: str) -> None:
        print("\n--- Prompt to paste into a chat model ---\n")
        print(prompt)
        print("\n--- End prompt ---\n")

    def _save_prompt(self, prompt: str) -> None:
        if self.prompt_path is None:
            return

        self.prompt_path.parent.mkdir(parents=True, exist_ok=True)
        self.prompt_path.write_text(prompt, encoding="utf-8")

    def _read_response(self) -> str:
        print("Paste the model response below. Press Ctrl-D when finished:\n")

        lines: list[str] = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            return "\n".join(lines).strip()
