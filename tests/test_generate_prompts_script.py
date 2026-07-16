"""Testes do comando de geração de prompts sem providers nem rede."""

from dataclasses import fields

import pytest
from openpyxl import Workbook

from scripts.generate_prompts_from_matrix import main
from src.matrix.models import MatrixRow


HEADERS = [field.name for field in fields(MatrixRow)]


def _row(number, provider="gemini", status="pending"):
    """Cria uma linha válida para exercitar filtros da CLI."""
    return {
        "matrix_row_id": number,
        "batch_id": f"B{number:04d}",
        "chunk_id": f"B{number:04d}_C01",
        "curriculum_level": "N1",
        "capability_code": "N1_explicit_fact_retrieval",
        "subskill_code": "N1A_direct_fact",
        "subskill_name": "Localizar facto",
        "subskill_description": "Localizar um facto explícito.",
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
        "assigned_provider": provider,
        "preferred_model": "provider-model",
        "prompt_version": "prompt_v1",
        "dataset_split_target": "train",
        "generation_status": status,
        "output_file": "",
        "notes": "",
    }


def _workbook(path, rows):
    """Escreve uma folha Matrix temporária para a CLI."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Matrix"
    worksheet.append(HEADERS)
    for row in rows:
        worksheet.append([row[header] for header in HEADERS])
    workbook.save(path)
    workbook.close()


def test_script_default_generation_and_summary(tmp_path, capsys):
    """Requisito: a CLI deve gerar por omissão todas as linhas pending.

    Resultado esperado: pares, manifesto e resumo refletem as duas linhas.
    """
    matrix = tmp_path / "matrix.xlsx"
    output = tmp_path / "prompts"
    _workbook(matrix, [_row(1), _row(2, provider="groq")])

    result = main(["--matrix", str(matrix), "--output-dir", str(output)])

    assert result == 0
    assert len(list(output.glob("*.prompt.txt"))) == 2
    assert len(list(output.glob("*.metadata.json"))) == 2
    assert (output / "manifest.jsonl").exists()
    summary = capsys.readouterr().out
    assert "Linhas da matriz lidas: 2" in summary
    assert "Linhas selecionadas: 2" in summary
    assert "Prompts escritos: 2" in summary
    assert "Providers representados: gemini, groq" in summary
    assert "Total de exemplos pedidos: 40" in summary


def test_script_status_filter(tmp_path):
    """Requisito: --status deve filtrar antes da escrita.

    Resultado esperado: apenas a linha generated produz um prompt.
    """
    matrix = tmp_path / "matrix.xlsx"
    output = tmp_path / "prompts"
    _workbook(matrix, [_row(1), _row(2, status="generated")])

    result = main(
        [
            "--matrix",
            str(matrix),
            "--output-dir",
            str(output),
            "--status",
            "generated",
        ]
    )

    assert result == 0
    assert [path.name for path in output.glob("*.prompt.txt")] == [
        "B0002_C01.prompt.txt"
    ]


def test_script_provider_filter(tmp_path):
    """Requisito: --provider deve filtrar após o estado.

    Resultado esperado: apenas a linha Groq pending é selecionada.
    """
    matrix = tmp_path / "matrix.xlsx"
    output = tmp_path / "prompts"
    _workbook(matrix, [_row(1), _row(2, provider="groq")])

    result = main(
        [
            "--matrix",
            str(matrix),
            "--output-dir",
            str(output),
            "--provider",
            "groq",
        ]
    )

    assert result == 0
    assert [path.name for path in output.glob("*.prompt.txt")] == [
        "B0002_C01.prompt.txt"
    ]


def test_script_applies_limit_after_filters(tmp_path):
    """Requisito: --limit deve ser aplicado depois dos filtros.

    Resultado esperado: apenas a primeira de três linhas elegíveis é escrita.
    """
    matrix = tmp_path / "matrix.xlsx"
    output = tmp_path / "prompts"
    _workbook(matrix, [_row(1), _row(2), _row(3)])

    result = main(
        [
            "--matrix",
            str(matrix),
            "--output-dir",
            str(output),
            "--limit",
            "1",
        ]
    )

    assert result == 0
    assert [path.name for path in output.glob("*.prompt.txt")] == [
        "B0001_C01.prompt.txt"
    ]


def test_script_rejects_non_positive_limit():
    """Requisito: --limit deve aceitar apenas inteiros positivos.

    Resultado esperado: argparse termina com código não zero para zero.
    """
    with pytest.raises(SystemExit) as error:
        main(["--limit", "0"])

    assert error.value.code != 0


def test_script_reports_no_selected_rows(tmp_path, capsys):
    """Requisito: filtros sem resultados devem produzir erro claro.

    Resultado esperado: a CLI devolve um e não cria pares nem manifesto.
    """
    matrix = tmp_path / "matrix.xlsx"
    output = tmp_path / "prompts"
    _workbook(matrix, [_row(1, provider="gemini")])

    result = main(
        [
            "--matrix",
            str(matrix),
            "--output-dir",
            str(output),
            "--provider",
            "cerebras",
        ]
    )

    assert result == 1
    assert "No matrix rows matched" in capsys.readouterr().err
    assert not output.exists()


def test_script_overwrite_behaviour(tmp_path):
    """Requisito: a CLI não substitui outputs sem --overwrite.

    Resultado esperado: segunda execução falha e a terceira com flag tem sucesso.
    """
    matrix = tmp_path / "matrix.xlsx"
    output = tmp_path / "prompts"
    _workbook(matrix, [_row(1)])
    arguments = ["--matrix", str(matrix), "--output-dir", str(output)]

    assert main(arguments) == 0
    assert main(arguments) == 1
    assert main(arguments + ["--overwrite"]) == 0
