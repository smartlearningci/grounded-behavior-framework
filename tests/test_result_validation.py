"""Testes da validação estrutural imutável."""

import json

from src.validation.result_validator import validate_result_file


def _outer(text, expected=2):
    return {
        "job": {"chunk_id": "chunk", "provider": "gemini", "examples_requested": expected},
        "request": {}, "result": {"text": text}, "execution": {},
    }


def _example(answer="Lisboa", context="A sede fica em Lisboa."):
    return {"context": context, "question": "Onde fica?", "answer": answer}


def _write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_valid_result_and_markdown_fence_are_accepted(tmp_path) -> None:
    """Requisito: JSON válido e fence externa. Resultado esperado: dois exemplos aceites."""
    generated = json.dumps({"examples": [_example(), _example("Porto", "A filial fica no Porto.")]})
    path = _write(tmp_path / "result.json", _outer(f"```json\n{generated}\n```"))

    result = validate_result_file(path)

    assert result.valid and result.status == "valid" and result.parsed_examples == 2


def test_invalid_outer_and_generated_json_are_distinguished(tmp_path) -> None:
    """Requisito: JSON em duas camadas. Resultado esperado: ambas as corrupções são invalid_json."""
    outer = tmp_path / "outer.json"
    outer.write_text("{bad", encoding="utf-8")
    generated = _write(tmp_path / "generated.json", _outer('{"examples": ['))

    assert validate_result_file(outer).status == "invalid_json"
    assert validate_result_file(generated).status == "invalid_json"


def test_truncation_is_detected_without_salvage_or_raw_change(tmp_path) -> None:
    """Requisito: truncatura sem salvamento. Resultado esperado: invalid_json, warning e bytes intactos."""
    text = '{"examples":[{"context":"ok","question":"q","answer":"ok"},{"context":"trunc'
    path = _write(tmp_path / "truncated.json", _outer(text))
    before = path.read_bytes()

    result = validate_result_file(path)

    assert result.status == "invalid_json" and result.parsed_examples == 0
    assert "likely_truncation" in result.warnings
    assert path.read_bytes() == before


def test_wrong_count_missing_and_empty_fields(tmp_path) -> None:
    """Requisito: contagem e schema. Resultado esperado: estados específicos sem aceitar campos vazios."""
    wrong = _write(tmp_path / "wrong.json", _outer(json.dumps({"examples": [_example()]})))
    missing = _write(
        tmp_path / "missing.json",
        _outer(json.dumps({"examples": [{"context": "x", "question": "q"}, _example()]})),
    )
    empty = _write(
        tmp_path / "empty.json",
        _outer(json.dumps({"examples": [{"context": "", "question": "q", "answer": "a"}, _example()]})),
    )

    assert validate_result_file(wrong).status == "wrong_example_count"
    assert validate_result_file(missing).status == "invalid_schema"
    assert validate_result_file(empty).status == "invalid_schema"


def test_answer_absent_from_context_is_rejected(tmp_path) -> None:
    """Requisito: grounding literal normalizado. Resultado esperado: answer_not_in_context."""
    payload = {"examples": [_example("Coimbra", "A sede fica em Lisboa."), _example()]}
    path = _write(tmp_path / "grounding.json", _outer(json.dumps(payload)))

    assert validate_result_file(path).status == "answer_not_in_context"


def test_missing_outer_keys_are_invalid_schema(tmp_path) -> None:
    """Requisito: envelope completo. Resultado esperado: chaves exteriores em falta são rejeitadas."""
    path = _write(tmp_path / "schema.json", {"job": {}, "result": {}})

    assert validate_result_file(path).status == "invalid_schema"
