"""Testes do comando que constrói a fila a partir do manifesto."""

import json

from scripts.build_generation_queue import main
from src.scheduling.queue import GenerationQueue


def _write_manifest(path) -> None:
    """Cria um manifesto pequeno com dois providers."""
    entries = []
    for number, provider in enumerate(("gemini", "groq"), start=1):
        chunk = f"B{number:04d}_C01"
        entries.append(
            {
                "matrix_row_id": number,
                "batch_id": f"B{number:04d}",
                "chunk_id": chunk,
                "assigned_provider": provider,
                "preferred_model": "model-a",
                "prompt_version": "n1_v1",
                "dataset_split_target": "train",
                "examples_per_prompt": 20,
                "prompt_file": f"{chunk}.prompt.txt",
                "metadata_file": f"{chunk}.metadata.json",
            }
        )
    path.write_text(
        "".join(json.dumps(entry) + "\n" for entry in entries),
        encoding="utf-8",
    )


def test_queue_creation_prints_required_summary(tmp_path, capsys) -> None:
    """Requisito: criar fila e resumo. Resultado esperado: dois jobs e 40 exemplos."""
    manifest = tmp_path / "manifest.jsonl"
    queue_path = tmp_path / "nested" / "jobs.jsonl"
    _write_manifest(manifest)

    result = main(["--manifest", str(manifest), "--queue", str(queue_path)])

    output = capsys.readouterr().out
    assert result == 0
    assert len(GenerationQueue(queue_path).load()) == 2
    assert "Entradas do manifesto: 2" in output
    assert "Jobs criados: 2" in output
    assert "gemini=1" in output and "groq=1" in output
    assert "Exemplos pedidos: 40" in output
    assert str(queue_path) in output


def test_existing_queue_is_refused_without_overwrite(tmp_path, capsys) -> None:
    """Requisito: recusar overwrite implícito. Resultado esperado: erro e bytes intactos."""
    manifest = tmp_path / "manifest.jsonl"
    queue_path = tmp_path / "jobs.jsonl"
    _write_manifest(manifest)
    queue_path.write_bytes(b"original\n")

    result = main(["--manifest", str(manifest), "--queue", str(queue_path)])

    assert result == 1
    assert queue_path.read_bytes() == b"original\n"
    assert "already exists" in capsys.readouterr().err


def test_overwrite_replaces_existing_queue(tmp_path) -> None:
    """Requisito: overwrite explícito. Resultado esperado: fila anterior é substituída."""
    manifest = tmp_path / "manifest.jsonl"
    queue_path = tmp_path / "jobs.jsonl"
    _write_manifest(manifest)
    queue_path.write_bytes(b"old\n")

    result = main(
        [
            "--manifest",
            str(manifest),
            "--queue",
            str(queue_path),
            "--overwrite",
        ]
    )

    assert result == 0
    assert len(GenerationQueue(queue_path).load()) == 2
