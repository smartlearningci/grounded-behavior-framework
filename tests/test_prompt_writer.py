"""Testes da escrita atómica de prompts e manifestos."""

import json
import os

import pytest

from src.matrix.models import MatrixRow
from src.prompts import writer
from src.prompts.writer import write_prompt_files, write_prompt_manifest


def _row(number=1, chunk_id="B0001_C01", domain="Bibliotecas"):
    """Cria uma linha válida para escrita em diretório temporário."""
    return MatrixRow(
        matrix_row_id=number,
        batch_id="B0001",
        chunk_id=chunk_id,
        curriculum_level="N1",
        capability_code="N1_explicit_fact_retrieval",
        subskill_code="N1A_direct_fact",
        subskill_name="Localizar facto",
        subskill_description="Localizar um facto explícito.",
        domain=domain,
        document_style="Notice",
        fact_type="Capacity",
        entity_type="Library",
        context_length="Short",
        fact_position="Beginning",
        distractor_type="D0_None",
        question_type="Q1_Direct",
        language="pt-PT",
        examples_per_prompt=20,
        assigned_provider="gemini",
        preferred_model="gemini-model",
        prompt_version="prompt_v1",
        dataset_split_target="train",
        generation_status="pending",
        output_file="outputs/result.json",
        notes="Revisão humana",
    )


def test_writer_creates_utf8_prompt_and_metadata_pair(tmp_path):
    """Requisito: cada linha deve produzir prompt e metadata em UTF-8.

    Resultado esperado: ambos os ficheiros existem e preservam caracteres pt-PT.
    """
    paths = write_prompt_files([_row(domain="Saúde Pública")], tmp_path)

    prompt_path = tmp_path / "B0001_C01.prompt.txt"
    metadata_path = tmp_path / "B0001_C01.metadata.json"
    assert paths == [prompt_path]
    assert "Saúde Pública" in prompt_path.read_text(encoding="utf-8")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["chunk_id"] == "B0001_C01"
    assert metadata["examples_per_prompt"] == 20


def test_writer_preserves_matrix_row_order(tmp_path):
    """Requisito: os caminhos devolvidos devem preservar a ordem da matriz.

    Resultado esperado: C02 permanece antes de C01 quando essa é a entrada.
    """
    rows = [
        _row(2, "B0001_C02"),
        _row(1, "B0001_C01"),
    ]

    paths = write_prompt_files(rows, tmp_path)

    assert [path.name for path in paths] == [
        "B0001_C02.prompt.txt",
        "B0001_C01.prompt.txt",
    ]


def test_writer_refuses_overwrite_by_default(tmp_path):
    """Requisito: ficheiros existentes não devem ser substituídos por omissão.

    Resultado esperado: FileExistsError ocorre sem alterar o conteúdo original.
    """
    row = _row()
    write_prompt_files([row], tmp_path)
    prompt_path = tmp_path / "B0001_C01.prompt.txt"
    original = prompt_path.read_text(encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        write_prompt_files([row], tmp_path)

    assert prompt_path.read_text(encoding="utf-8") == original


def test_writer_overwrite_replaces_both_files(tmp_path):
    """Requisito: overwrite deve substituir prompt e metadata do mesmo chunk.

    Resultado esperado: ambos os ficheiros refletem os novos valores da linha.
    """
    write_prompt_files([_row(domain="Bibliotecas")], tmp_path)

    write_prompt_files([_row(domain="Saúde Pública")], tmp_path, overwrite=True)

    prompt = (tmp_path / "B0001_C01.prompt.txt").read_text(encoding="utf-8")
    metadata = json.loads(
        (tmp_path / "B0001_C01.metadata.json").read_text(encoding="utf-8")
    )
    assert "Saúde Pública" in prompt
    assert metadata["domain"] == "Saúde Pública"


def test_writer_leaves_no_partial_pair_after_commit_failure(tmp_path, monkeypatch):
    """Requisito: uma falha de publicação não pode deixar apenas um ficheiro.

    Resultado esperado: prompt, metadata e temporários são removidos após o erro.
    """
    real_replace = os.replace
    calls = 0

    def fail_second_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated commit failure")
        return real_replace(source, destination)

    monkeypatch.setattr(writer.os, "replace", fail_second_replace)

    with pytest.raises(OSError, match="simulated commit failure"):
        write_prompt_files([_row()], tmp_path)

    assert not (tmp_path / "B0001_C01.prompt.txt").exists()
    assert not (tmp_path / "B0001_C01.metadata.json").exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_writer_rejects_duplicate_destination_names(tmp_path):
    """Requisito: dois chunks não podem resolver para o mesmo nome de ficheiro.

    Resultado esperado: ValueError ocorre antes de escrever qualquer destino.
    """
    rows = [_row(1, "duplicate"), _row(2, "duplicate")]

    with pytest.raises(ValueError, match="Duplicate prompt destination"):
        write_prompt_files(rows, tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_manifest_contains_relative_files_and_preserves_order(tmp_path):
    """Requisito: o manifesto deve combinar metadata e estado pela ordem Matrix.

    Resultado esperado: linhas JSONL usam apenas nomes relativos de ficheiros.
    """
    rows = [_row(2, "B0001_C02"), _row(1, "B0001_C01")]

    manifest = write_prompt_manifest(rows, tmp_path)

    entries = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
    ]
    assert [entry["chunk_id"] for entry in entries] == [
        "B0001_C02",
        "B0001_C01",
    ]
    assert entries[0]["prompt_file"] == "B0001_C02.prompt.txt"
    assert entries[0]["metadata_file"] == "B0001_C02.metadata.json"
    assert entries[0]["generation_status"] == "pending"
    assert entries[0]["output_file"] == "outputs/result.json"
    assert entries[0]["notes"] == "Revisão humana"
    assert not entries[0]["prompt_file"].startswith("/")


def test_manifest_obeys_overwrite_flag(tmp_path):
    """Requisito: o manifesto deve respeitar a mesma política de overwrite.

    Resultado esperado: a segunda escrita falha sem flag e funciona com a flag.
    """
    row = _row()
    write_prompt_manifest([row], tmp_path)

    with pytest.raises(FileExistsError, match="already exists"):
        write_prompt_manifest([row], tmp_path)

    path = write_prompt_manifest([row], tmp_path, overwrite=True)
    assert path == tmp_path / "manifest.jsonl"
