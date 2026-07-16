"""Testes do arquivo seguro de uma execução."""

import json
from pathlib import Path

from scripts.archive_generation_run import archive_generation_run
from src.scheduling.models import GenerationJob, utc_now_iso
from src.scheduling.queue import GenerationQueue


def _run_tree(root: Path):
    prompts = root / "prompts"
    runtime = root / "runtime"
    raw = root / "raw"
    prompts.mkdir(); runtime.mkdir(); (raw / "gemini").mkdir(parents=True)
    (prompts / "manifest.jsonl").write_text("{}\n", encoding="utf-8")
    (prompts / "chunk.prompt.txt").write_text("prompt", encoding="utf-8")
    (runtime / "rate_limiter_state.json").write_text("{}", encoding="utf-8")
    result = raw / "gemini" / "chunk.result.json"
    result.write_text(json.dumps({"job": {"provider": "gemini"}}), encoding="utf-8")
    (raw / ".env").write_text("API_KEY=secret", encoding="utf-8")
    now = utc_now_iso()
    job = GenerationJob(
        "job_chunk", 1, "batch", "chunk", "gemini", "model", "n1_v1", "train",
        20, "chunk.prompt.txt", "chunk.json", "completed", 1, now, now, "", str(result),
    )
    queue = GenerationQueue(root / "queue" / "jobs.jsonl")
    queue.save([job])
    return prompts, queue.path, runtime, raw


def test_archive_dry_run_changes_nothing_and_excludes_secrets(tmp_path) -> None:
    """Requisito: dry-run e secrets excluídos. Resultado esperado: plano sem diretório nem .env."""
    prompts, queue, runtime, raw = _run_tree(tmp_path)
    destination, manifest = archive_generation_run(
        "n1_v1", "pilot", prompts, queue, runtime, raw,
        archive_root=tmp_path / "archive", dry_run=True,
        repository_root=tmp_path, timestamp="20260101T000000Z",
    )

    assert not destination.exists()
    assert not any(entry["source_path"].endswith(".env") for entry in manifest["files"])
    assert manifest["result_count"] == 1
    assert manifest["provider_counts"] == {"gemini": 1}
    assert Path(queue).exists() and (raw / "gemini" / "chunk.result.json").exists()


def test_real_archive_writes_manifest_and_preserves_sources(tmp_path) -> None:
    """Requisito: arquivo auditável sem deleção. Resultado esperado: hashes, resumo e origens intactas."""
    prompts, queue, runtime, raw = _run_tree(tmp_path)
    destination, manifest = archive_generation_run(
        "n1_v1", "pilot", prompts, queue, runtime, raw,
        archive_root=tmp_path / "archive", repository_root=tmp_path,
        timestamp="20260101T000000Z",
    )

    stored = json.loads((destination / "archive_manifest.json").read_text())
    assert stored["files"] == manifest["files"]
    assert stored["queue_summary"]["completed"] == 1
    assert all(len(entry["sha256"]) == 64 and entry["byte_size"] >= 0 for entry in stored["files"])
    assert Path(queue).exists() and prompts.exists() and runtime.exists() and raw.exists()
