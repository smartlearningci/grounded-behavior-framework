"""Testes do leitor da folha Matrix com workbooks temporários."""

from dataclasses import fields

import pytest
from openpyxl import Workbook

from src.matrix.models import MatrixRow
from src.matrix.reader import read_matrix


HEADERS = [field.name for field in fields(MatrixRow)]


def _valid_row(**overrides):
    """Cria valores válidos para uma linha temporária."""
    values = {
        "matrix_row_id": 1,
        "batch_id": "B0001",
        "chunk_id": "B0001_C01",
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
        "assigned_provider": "gemini",
        "preferred_model": "model-a",
        "prompt_version": "prompt_v1",
        "dataset_split_target": "train",
        "generation_status": "pending",
        "output_file": None,
        "notes": None,
    }
    values.update(overrides)
    return values


def _write_workbook(path, rows, headers=None, sheet_name="Matrix"):
    """Escreve um workbook mínimo usado exclusivamente pelo teste."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    selected_headers = headers or HEADERS
    worksheet.append(selected_headers)
    for row in rows:
        if row is None:
            worksheet.append([None] * len(selected_headers))
        else:
            worksheet.append([row.get(header) for header in selected_headers])
    workbook.save(path)
    workbook.close()


def test_read_valid_matrix_and_convert_empty_strings(tmp_path):
    """Requisito: uma folha válida deve produzir MatrixRow na ordem original.

    Resultado esperado: campos vazios tornam-se strings vazias e to_dict funciona.
    """
    path = tmp_path / "matrix.xlsx"
    _write_workbook(path, [_valid_row()])

    rows = read_matrix(path)

    assert len(rows) == 1
    assert isinstance(rows[0], MatrixRow)
    assert rows[0].output_file == ""
    assert rows[0].notes == ""
    assert rows[0].to_dict()["chunk_id"] == "B0001_C01"


def test_read_matrix_missing_file(tmp_path):
    """Requisito: o ficheiro da matriz deve existir.

    Resultado esperado: FileNotFoundError identifica o caminho ausente.
    """
    with pytest.raises(FileNotFoundError, match="does not exist"):
        read_matrix(tmp_path / "missing.xlsx")


def test_read_matrix_missing_sheet(tmp_path):
    """Requisito: a folha pedida deve existir no workbook.

    Resultado esperado: ValueError identifica a folha Matrix ausente.
    """
    path = tmp_path / "matrix.xlsx"
    _write_workbook(path, [_valid_row()], sheet_name="Other")

    with pytest.raises(ValueError, match="Matrix sheet does not exist"):
        read_matrix(path)


def test_read_matrix_missing_required_header(tmp_path):
    """Requisito: todos os cabeçalhos MatrixRow são obrigatórios.

    Resultado esperado: ValueError enumera o cabeçalho notes removido.
    """
    path = tmp_path / "matrix.xlsx"
    _write_workbook(path, [_valid_row()], headers=HEADERS[:-1])

    with pytest.raises(ValueError, match="notes"):
        read_matrix(path)


def test_read_matrix_ignores_extra_unknown_column(tmp_path):
    """Requisito: colunas desconhecidas não devem alterar MatrixRow.

    Resultado esperado: a linha é lida e a coluna extra é ignorada.
    """
    path = tmp_path / "matrix.xlsx"
    row = _valid_row(extra_column="ignored")
    _write_workbook(path, [row], headers=HEADERS + ["extra_column"])

    rows = read_matrix(path)

    assert rows[0].chunk_id == "B0001_C01"
    assert "extra_column" not in rows[0].to_dict()


def test_read_matrix_ignores_completely_empty_row(tmp_path):
    """Requisito: linhas completamente vazias não representam chunks.

    Resultado esperado: apenas as duas linhas preenchidas são devolvidas.
    """
    path = tmp_path / "matrix.xlsx"
    _write_workbook(
        path,
        [
            _valid_row(),
            None,
            _valid_row(matrix_row_id=2, chunk_id="B0001_C02"),
        ],
    )

    rows = read_matrix(path)

    assert [row.chunk_id for row in rows] == ["B0001_C01", "B0001_C02"]


def test_read_matrix_strips_whitespace(tmp_path):
    """Requisito: células textuais devem perder whitespace exterior.

    Resultado esperado: batch_id, chunk_id e domínio ficam normalizados.
    """
    path = tmp_path / "matrix.xlsx"
    _write_workbook(
        path,
        [_valid_row(batch_id=" B0001 ", chunk_id=" B0001_C01 ", domain=" Saúde ")],
    )

    row = read_matrix(path)[0]

    assert (row.batch_id, row.chunk_id, row.domain) == (
        "B0001",
        "B0001_C01",
        "Saúde",
    )


def test_read_matrix_converts_numeric_fields_to_int(tmp_path):
    """Requisito: identificador e quantidade devem ser inteiros.

    Resultado esperado: valores numéricos Excel e textuais tornam-se int.
    """
    path = tmp_path / "matrix.xlsx"
    _write_workbook(path, [_valid_row(matrix_row_id=1.0, examples_per_prompt="20")])

    row = read_matrix(path)[0]

    assert row.matrix_row_id == 1
    assert row.examples_per_prompt == 20
    assert isinstance(row.examples_per_prompt, int)


@pytest.mark.parametrize(
    ("field_name", "duplicate_value", "message"),
    [
        ("chunk_id", "B0001_C01", "Duplicate chunk_id"),
        ("matrix_row_id", 1, "Duplicate matrix_row_id"),
    ],
)
def test_read_matrix_rejects_duplicate_identifiers(
    tmp_path,
    field_name,
    duplicate_value,
    message,
):
    """Requisito: chunk_id e matrix_row_id devem ser únicos.

    Resultado esperado: ValueError identifica o tipo de duplicado encontrado.
    """
    path = tmp_path / "matrix.xlsx"
    second = _valid_row(matrix_row_id=2, chunk_id="B0001_C02")
    second[field_name] = duplicate_value
    _write_workbook(path, [_valid_row(), second])

    with pytest.raises(ValueError, match=message):
        read_matrix(path)


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("assigned_provider", "unknown", "invalid assigned_provider"),
        ("generation_status", "unknown", "invalid generation_status"),
        ("dataset_split_target", "unknown", "invalid dataset_split_target"),
        ("examples_per_prompt", 0, "greater than zero"),
    ],
)
def test_read_matrix_rejects_invalid_operational_values(
    tmp_path,
    field_name,
    invalid_value,
    message,
):
    """Requisito: valores operacionais devem respeitar os controlos definidos.

    Resultado esperado: cada provider, estado, split ou quantidade inválida falha.
    """
    path = tmp_path / "matrix.xlsx"
    _write_workbook(path, [_valid_row(**{field_name: invalid_value})])

    with pytest.raises(ValueError, match=message):
        read_matrix(path)


def test_read_matrix_rejects_empty_matrix(tmp_path):
    """Requisito: uma matriz sem chunks não é válida.

    Resultado esperado: ValueError indica que a matriz não pode estar vazia.
    """
    path = tmp_path / "matrix.xlsx"
    _write_workbook(path, [])

    with pytest.raises(ValueError, match="must not be empty"):
        read_matrix(path)
