"""Escreve prompts, metadados e manifestos de forma atómica."""

import json
import os
import tempfile
from pathlib import Path

from src.matrix.models import MatrixRow

from .builder import build_generation_prompt, build_prompt_metadata


def write_prompt_files(
    rows: list[MatrixRow],
    output_dir: str | Path,
    overwrite: bool = False,
) -> list[Path]:
    """Cria um ficheiro de prompt e um de metadados por linha."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    pairs = _destination_pairs(rows, destination)

    if not overwrite:
        existing = [
            path
            for prompt_path, metadata_path in pairs
            for path in (prompt_path, metadata_path)
            if path.exists()
        ]
        if existing:
            raise FileExistsError(f"Destination file already exists: {existing[0]}")

    prompt_paths: list[Path] = []
    for row, (prompt_path, metadata_path) in zip(rows, pairs):
        prompt_text = build_generation_prompt(row)
        metadata_text = json.dumps(
            build_prompt_metadata(row),
            ensure_ascii=False,
            indent=2,
        ) + "\n"
        temporary_paths: list[Path] = []
        try:
            temporary_prompt = _write_temporary_text(
                destination,
                prompt_path.name,
                prompt_text,
            )
            temporary_paths.append(temporary_prompt)
            temporary_metadata = _write_temporary_text(
                destination,
                metadata_path.name,
                metadata_text,
            )
            temporary_paths.append(temporary_metadata)
            _commit_pair(
                temporary_prompt,
                temporary_metadata,
                prompt_path,
                metadata_path,
                overwrite,
            )
            prompt_paths.append(prompt_path)
        finally:
            for temporary_path in temporary_paths:
                temporary_path.unlink(missing_ok=True)

    return prompt_paths


def write_prompt_manifest(
    rows: list[MatrixRow],
    output_dir: str | Path,
    filename: str = "manifest.jsonl",
    overwrite: bool = False,
) -> Path:
    """Escreve um manifesto JSONL pela ordem original das linhas."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / filename
    if manifest_path.exists() and not overwrite:
        raise FileExistsError(f"Destination file already exists: {manifest_path}")

    lines = []
    for row in rows:
        entry = build_prompt_metadata(row)
        entry.update(
            {
                "prompt_file": f"{row.chunk_id}.prompt.txt",
                "metadata_file": f"{row.chunk_id}.metadata.json",
                "generation_status": row.generation_status,
                "output_file": row.output_file,
                "notes": row.notes,
            }
        )
        lines.append(json.dumps(entry, ensure_ascii=False))
    content = "\n".join(lines)
    if lines:
        content += "\n"

    temporary_path = _write_temporary_text(
        destination,
        manifest_path.name,
        content,
    )
    try:
        os.replace(temporary_path, manifest_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return manifest_path


def _destination_pairs(
    rows: list[MatrixRow],
    output_dir: Path,
) -> list[tuple[Path, Path]]:
    """Calcula destinos e rejeita nomes repetidos antes de escrever."""
    pairs = [
        (
            output_dir / f"{row.chunk_id}.prompt.txt",
            output_dir / f"{row.chunk_id}.metadata.json",
        )
        for row in rows
    ]
    names = [path.name for pair in pairs for path in pair]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate prompt destination filename")
    return pairs


def _write_temporary_text(
    output_dir: Path,
    target_name: str,
    content: str,
) -> Path:
    """Escreve conteúdo UTF-8 num ficheiro temporário no destino."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_dir,
        prefix=f".{target_name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_file.write(content)
        return Path(temporary_file.name)


def _commit_pair(
    temporary_prompt: Path,
    temporary_metadata: Path,
    prompt_path: Path,
    metadata_path: Path,
    overwrite: bool,
) -> None:
    """Publica o par e repõe os destinos anteriores se uma operação falhar."""
    targets = (prompt_path, metadata_path)
    temporary_files = (temporary_prompt, temporary_metadata)
    backups: dict[Path, Path] = {}
    committed: list[Path] = []

    try:
        if overwrite:
            for target in targets:
                if target.exists():
                    backup = _unused_temporary_path(target.parent, target.name)
                    os.replace(target, backup)
                    backups[target] = backup

        for temporary_file, target in zip(temporary_files, targets):
            os.replace(temporary_file, target)
            committed.append(target)
    except Exception:
        for target in committed:
            target.unlink(missing_ok=True)
        for target, backup in backups.items():
            if backup.exists():
                os.replace(backup, target)
        raise
    else:
        for backup in backups.values():
            backup.unlink(missing_ok=True)


def _unused_temporary_path(output_dir: Path, target_name: str) -> Path:
    """Reserva um nome temporário inexistente para guardar um backup."""
    with tempfile.NamedTemporaryFile(
        dir=output_dir,
        prefix=f".{target_name}.",
        suffix=".bak",
        delete=False,
    ) as temporary_file:
        path = Path(temporary_file.name)
    path.unlink()
    return path
