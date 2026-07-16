"""Copia uma execução para arquivo sem apagar os artefactos de origem."""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scheduling.queue import GenerationQueue  # noqa: E402


def archive_generation_run(
    version: str,
    label: str,
    prompts_dir: str | Path,
    queue_path: str | Path,
    runtime_dir: str | Path,
    raw_dir: str | Path,
    archive_root: str | Path = "artifacts/archive",
    dry_run: bool = False,
    repository_root: str | Path = PROJECT_ROOT,
    timestamp: str | None = None,
) -> tuple[Path, dict[str, object]]:
    """Planeia ou copia ficheiros regulares confinados à raiz indicada."""
    root = Path(repository_root).resolve()
    safe_version = _safe_label(version, "version")
    safe_label = _safe_label(label, "label")
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_base = _inside(root, archive_root, "archive root")
    destination_root = archive_base / safe_version / f"{stamp}_{safe_label}"
    if destination_root.exists():
        raise FileExistsError(f"Archive destination already exists: {destination_root}")

    sources = {
        "prompts": _inside(root, prompts_dir, "prompts directory"),
        "queue": _inside(root, queue_path, "queue"),
        "runtime": _inside(root, runtime_dir, "runtime directory"),
        "raw": _inside(root, raw_dir, "raw directory"),
    }
    operations: list[tuple[Path, Path]] = []
    for category, source in sources.items():
        if not source.exists():
            continue
        if source.is_symlink():
            raise ValueError(f"Unsafe symbolic link: {source}")
        if source.is_file():
            if not _secret_filename(source.name):
                operations.append((source, destination_root / category / source.name))
        else:
            for item in sorted(source.rglob("*")):
                if item.is_symlink():
                    raise ValueError(f"Unsafe symbolic link: {item}")
                if (
                    item.is_file()
                    and not _secret_filename(item.name)
                    and _include_category_file(category, item.name)
                ):
                    operations.append((item, destination_root / category / item.relative_to(source)))

    provider_counts: Counter[str] = Counter()
    result_count = 0
    entries = []
    for source, destination in operations:
        data = source.read_bytes()
        entries.append(
            {
                "source_path": str(source),
                "destination_path": str(destination),
                "sha256": hashlib.sha256(data).hexdigest(),
                "byte_size": len(data),
            }
        )
        if source.name.endswith(".result.json"):
            result_count += 1
            try:
                payload = json.loads(data)
                provider = payload.get("job", {}).get("provider")
                if isinstance(provider, str):
                    provider_counts[provider] += 1
            except (UnicodeError, json.JSONDecodeError, AttributeError):
                pass
    queue_summary = (
        GenerationQueue(sources["queue"]).summary()
        if sources["queue"].is_file()
        else {}
    )
    manifest = {
        "version": safe_version,
        "label": safe_label,
        "archive_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_paths": {key: str(value) for key, value in sources.items()},
        "archive_path": str(destination_root),
        "files": entries,
        "queue_summary": queue_summary,
        "result_count": result_count,
        "provider_counts": dict(provider_counts),
    }
    for source, destination in operations:
        print(f"COPY {source} -> {destination}")
    print(f"WRITE archive_manifest.json -> {destination_root / 'archive_manifest.json'}")
    if dry_run:
        return destination_root, manifest

    for source, destination in operations:
        _atomic_copy(source, destination)
    _atomic_json(destination_root / "archive_manifest.json", manifest)
    return destination_root, manifest


def _inside(root: Path, value: str | Path, label: str) -> Path:
    """Resolve caminhos relativos à raiz e rejeita qualquer fuga."""
    path = Path(value)
    resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"{label} must be inside repository: {resolved}")
    return resolved


def _safe_label(value: str, label: str) -> str:
    """Limita nomes de diretório a caracteres portáveis."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value) or value in {".", ".."}:
        raise ValueError(f"Invalid archive {label}: {value}")
    return value


def _secret_filename(name: str) -> bool:
    """Exclui ficheiros de ambiente e credenciais pelo nome."""
    lowered = name.lower()
    return (
        lowered == ".env"
        or lowered.startswith(".env.")
        or any(term in lowered for term in ("api_key", "credential", "secret", "token"))
    )


def _include_category_file(category: str, name: str) -> bool:
    """No raw, limita o arquivo a artefactos conhecidos da geração."""
    if category != "raw":
        return True
    return name.endswith(
        (".result.json", ".failure.json", ".validation.json", ".prompt.txt")
    )


def _atomic_copy(source: Path, destination: Path) -> None:
    """Copia primeiro para temporário e publica por rename."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as file:
        temporary = Path(file.name)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, payload: object) -> None:
    """Escreve o manifesto UTF-8 de forma atómica."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
        temporary = Path(file.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    """Define origens explícitas e confirmação do arquivo."""
    parser = argparse.ArgumentParser(description="Arquiva uma execução sem apagar origens.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--prompts-dir", required=True)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--archive-root", default="artifacts/archive")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Recusa escrita sem --yes e executa o plano seguro."""
    arguments = build_parser().parse_args(argv)
    if not arguments.dry_run and not arguments.yes:
        print("Erro: --yes é obrigatório para criar o arquivo.", file=sys.stderr)
        return 2
    try:
        destination, manifest = archive_generation_run(
            arguments.version, arguments.label, arguments.prompts_dir,
            arguments.queue, arguments.runtime_dir, arguments.raw_dir,
            arguments.archive_root, arguments.dry_run,
        )
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(f"Archive: {destination}")
    print(f"Files: {len(manifest['files'])}")
    print(f"Results: {manifest['result_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
