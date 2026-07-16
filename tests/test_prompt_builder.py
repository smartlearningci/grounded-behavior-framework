"""Testes da construção determinística das prompts de geração."""

import pytest

from src.matrix.models import MatrixRow
from src.prompts.builder import build_generation_prompt, build_prompt_metadata


def _row(**overrides):
    """Cria uma MatrixRow válida para testar texto e metadata."""
    values = {
        "matrix_row_id": 1,
        "batch_id": "B0001",
        "chunk_id": "B0001_C01",
        "curriculum_level": "N1",
        "capability_code": "N1_explicit_fact_retrieval",
        "subskill_code": "N1A_direct_fact",
        "subskill_name": "Localizar facto explícito direto",
        "subskill_description": "Localizar um facto explicitamente escrito.",
        "domain": "Bibliotecas",
        "document_style": "Notice",
        "fact_type": "Capacity",
        "entity_type": "Library",
        "context_length": "Short",
        "fact_position": "Beginning",
        "distractor_type": "D0_None",
        "question_type": "Q1_Direct",
        "language": "pt-PT",
        "examples_per_prompt": 20,
        "assigned_provider": "secret-provider",
        "preferred_model": "secret-model",
        "prompt_version": "prompt_v1",
        "dataset_split_target": "train",
        "generation_status": "pending",
        "output_file": "",
        "notes": "",
    }
    values.update(overrides)
    return MatrixRow(**values)


def test_prompt_contains_identifiers_dimensions_and_exact_count():
    """Requisito: a prompt deve conter IDs, objetivo e dimensões controladas.

    Resultado esperado: os 20 exemplos e todas as instruções aparecem em pt-PT.
    """
    prompt = build_generation_prompt(_row())

    for expected in (
        "Gera exatamente 20 exemplos",
        "B0001_C01",
        "N1_explicit_fact_retrieval",
        "N1A_direct_fact",
        "Localizar facto explícito direto",
        "Localizar um facto explicitamente escrito.",
        "Bibliotecas",
        "aviso",
        "capacidade",
        "biblioteca",
        "curto, com 3 a 5 frases",
        "no início do contexto",
        "não incluir distratores relevantes",
        "pergunta direta",
        "português europeu (pt-PT)",
    ):
        assert expected in prompt


def test_prompt_contains_strict_json_envelope_and_rules():
    """Requisito: a prompt deve exigir envelope JSON e regras de grounding.

    Resultado esperado: context, question e answer aparecem sem Markdown externo.
    """
    prompt = build_generation_prompt(_row())

    assert '"examples": [' in prompt
    assert '"context": "..."' in prompt
    assert '"question": "..."' in prompt
    assert '"answer": "..."' in prompt
    assert "sem Markdown" in prompt
    assert "Não acrescentes explicações" in prompt
    assert "única resposta correta" in prompt
    assert "totalmente suportada pelo contexto" in prompt
    assert "Não repitas nem dupliques exemplos" in prompt


def test_prompt_excludes_provider_and_model():
    """Requisito: provider e modelo pertencem apenas aos metadados.

    Resultado esperado: os valores secretos não aparecem no texto da prompt.
    """
    prompt = build_generation_prompt(_row())

    assert "secret-provider" not in prompt
    assert "secret-model" not in prompt


def test_prompt_metadata_contains_exact_execution_fields():
    """Requisito: metadata deve conter apenas os doze campos pedidos.

    Resultado esperado: provider e modelo são preservados sem incluir secrets.
    """
    metadata = build_prompt_metadata(_row())

    assert list(metadata) == [
        "matrix_row_id",
        "batch_id",
        "chunk_id",
        "curriculum_level",
        "capability_code",
        "subskill_code",
        "domain",
        "assigned_provider",
        "preferred_model",
        "prompt_version",
        "dataset_split_target",
        "examples_per_prompt",
    ]
    assert metadata["assigned_provider"] == "secret-provider"
    assert metadata["preferred_model"] == "secret-model"


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        ("context_length", "Unknown context_length"),
        ("fact_position", "Unknown fact_position"),
        ("distractor_type", "Unknown distractor_type"),
        ("question_type", "Unknown question_type"),
        ("document_style", "Unknown document_style"),
    ],
)
def test_prompt_rejects_unknown_controlled_values(field_name, message):
    """Requisito: dimensões controladas desconhecidas não podem ser suavizadas.

    Resultado esperado: ValueError identifica precisamente a dimensão inválida.
    """
    with pytest.raises(ValueError, match=message):
        build_generation_prompt(_row(**{field_name: "Unknown"}))


def test_prompt_output_is_deterministic():
    """Requisito: a mesma MatrixRow deve produzir sempre o mesmo texto.

    Resultado esperado: duas construções independentes são exatamente iguais.
    """
    row = _row()

    assert build_generation_prompt(row) == build_generation_prompt(row)
