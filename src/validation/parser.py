"""Prepara e analisa apenas o JSON devolvido pelo modelo."""

import json
import re


def strip_outer_markdown_fence(text: str) -> str:
    """Remove exclusivamente uma fence externa completa, com ou sem json."""
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", stripped, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else stripped


def parse_generated_json(text: str) -> tuple[object | None, str | None, list[str]]:
    """Devolve payload, erro e avisos de truncatura sem tentar salvamento parcial."""
    prepared = strip_outer_markdown_fence(text)
    try:
        return json.loads(prepared), None, []
    except json.JSONDecodeError as exc:
        warnings = detect_truncation(prepared, exc)
        return None, f"Generated JSON is invalid: {exc}", warnings


def detect_truncation(text: str, error: json.JSONDecodeError) -> list[str]:
    """Deteta sinais conservadores de output interrompido perto do fim."""
    indicators: list[str] = []
    message = error.msg.lower()
    if "unterminated string" in message:
        indicators.append("unterminated_json_string")
    if text.count("{") > text.count("}") or text.count("[") > text.count("]"):
        indicators.append("incomplete_json_container")
    contexts = len(re.findall(r'"context"\s*:', text))
    questions = len(re.findall(r'"question"\s*:', text))
    answers = len(re.findall(r'"answer"\s*:', text))
    if contexts > questions or contexts > answers:
        indicators.append("more_context_keys_than_question_or_answer")
    if error.pos >= max(0, len(text) - 300):
        indicators.append("parser_error_near_end")
    tail = text.rstrip()
    if tail and tail[-1] not in "}].\"'!?…":
        indicators.append("output_ends_mid_sentence")
    if indicators:
        return ["likely_truncation"] + indicators
    return []
