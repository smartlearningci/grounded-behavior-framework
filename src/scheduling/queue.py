"""Persistência JSONL atómica da fila de geração."""

import json
import os
import tempfile
from pathlib import Path

from .models import GenerationJob, VALID_JOB_STATUSES, utc_now_iso


MANIFEST_REQUIRED_FIELDS = (
    "matrix_row_id",
    "batch_id",
    "chunk_id",
    "assigned_provider",
    "preferred_model",
    "prompt_version",
    "dataset_split_target",
    "examples_per_prompt",
    "prompt_file",
    "metadata_file",
)


class GenerationQueue:
    """Mantém uma fila ordenada num único ficheiro JSONL."""

    def __init__(self, path: str | Path) -> None:
        """Configura o caminho persistente sem criar o ficheiro."""
        self.path = Path(path)

    def load(self) -> list[GenerationJob]:
        """Carrega a fila; um caminho ausente representa uma fila vazia."""
        if not self.path.exists():
            return []
        jobs: list[GenerationJob] = []
        with self.path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    jobs.append(GenerationJob.from_dict(data))
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Malformed queue JSONL at line {line_number}: {exc}"
                    ) from exc
        _validate_unique_jobs(jobs)
        return jobs

    def save(self, jobs: list[GenerationJob]) -> None:
        """Substitui a fila por uma escrita temporária e rename atómico."""
        _validate_unique_jobs(jobs)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = "".join(
            json.dumps(job.to_dict(), ensure_ascii=False) + "\n" for job in jobs
        )
        temporary_path = _write_temporary(self.path, content)
        try:
            os.replace(temporary_path, self.path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def add_jobs(
        self,
        jobs: list[GenerationJob],
        overwrite: bool = False,
    ) -> None:
        """Acrescenta jobs ou substitui explicitamente toda a fila."""
        if overwrite:
            self.save(jobs)
            return
        existing = self.load()
        self.save(existing + jobs)

    def get_jobs(self, status: str | None = None) -> list[GenerationJob]:
        """Devolve todos os jobs ou apenas os que têm o estado indicado."""
        if status is not None and status not in VALID_JOB_STATUSES:
            raise ValueError(f"Invalid GenerationJob status: {status}")
        jobs = self.load()
        if status is None:
            return jobs
        return [job for job in jobs if job.status == status]

    def update_job(self, job: GenerationJob) -> None:
        """Atualiza um job existente, o timestamp e preserva a ordem."""
        jobs = self.load()
        for index, existing in enumerate(jobs):
            if existing.job_id == job.job_id:
                job.updated_at = utc_now_iso()
                jobs[index] = job
                self.save(jobs)
                return
        raise KeyError(f"Queue job does not exist: {job.job_id}")

    def reset_running_jobs(self) -> int:
        """Recupera jobs interrompidos, mudando running para pending."""
        jobs = self.load()
        changed = 0
        timestamp = utc_now_iso()
        for job in jobs:
            if job.status == "running":
                job.status = "pending"
                job.updated_at = timestamp
                changed += 1
        if changed:
            self.save(jobs)
        return changed

    def summary(self) -> dict[str, int]:
        """Conta jobs por cada estado conhecido, incluindo estados sem jobs."""
        counts = {status: 0 for status in VALID_JOB_STATUSES}
        for job in self.load():
            counts[job.status] += 1
        return counts


def build_jobs_from_manifest(
    manifest_path: str | Path,
) -> list[GenerationJob]:
    """Converte cada entrada do manifesto num job pending determinístico."""
    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"Prompt manifest does not exist: {path}")

    jobs: list[GenerationJob] = []
    seen_chunks: set[str] = set()
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Malformed manifest JSONL at line {line_number}: {exc}"
                ) from exc
            if not isinstance(data, dict):
                raise ValueError(
                    f"Malformed manifest JSONL at line {line_number}: expected object"
                )
            missing = [field for field in MANIFEST_REQUIRED_FIELDS if field not in data]
            if missing:
                raise ValueError(
                    f"Manifest line {line_number} is missing fields: "
                    + ", ".join(missing)
                )

            chunk_id = str(data["chunk_id"])
            if chunk_id in seen_chunks:
                raise ValueError(f"Duplicate manifest chunk_id: {chunk_id}")
            seen_chunks.add(chunk_id)
            prompt_file = str(data["prompt_file"])
            metadata_file = str(data["metadata_file"])
            if Path(prompt_file).is_absolute() or Path(metadata_file).is_absolute():
                raise ValueError(
                    f"Manifest line {line_number} must use relative prompt filenames"
                )
            timestamp = utc_now_iso()
            try:
                job = GenerationJob(
                    job_id=f"job_{chunk_id}",
                    matrix_row_id=_manifest_int(
                        data["matrix_row_id"],
                        "matrix_row_id",
                        line_number,
                    ),
                    batch_id=str(data["batch_id"]),
                    chunk_id=chunk_id,
                    provider=str(data["assigned_provider"]),
                    preferred_model=str(data["preferred_model"]),
                    prompt_version=str(data["prompt_version"]),
                    dataset_split_target=str(data["dataset_split_target"]),
                    examples_requested=_manifest_int(
                        data["examples_per_prompt"],
                        "examples_per_prompt",
                        line_number,
                    ),
                    prompt_file=prompt_file,
                    metadata_file=metadata_file,
                    status="pending",
                    attempt_count=0,
                    created_at=timestamp,
                    updated_at=timestamp,
                    last_error="",
                    result_file="",
                )
            except ValueError as exc:
                raise ValueError(f"Malformed manifest line {line_number}: {exc}") from exc
            jobs.append(job)
    _validate_unique_jobs(jobs)
    return jobs


def _validate_unique_jobs(jobs: list[GenerationJob]) -> None:
    """Rejeita identificadores de job ou chunk repetidos."""
    job_ids: set[str] = set()
    chunk_ids: set[str] = set()
    for job in jobs:
        if job.job_id in job_ids:
            raise ValueError(f"Duplicate queue job_id: {job.job_id}")
        if job.chunk_id in chunk_ids:
            raise ValueError(f"Duplicate queue chunk_id: {job.chunk_id}")
        job_ids.add(job.job_id)
        chunk_ids.add(job.chunk_id)


def _write_temporary(path: Path, content: str) -> Path:
    """Cria o ficheiro temporário UTF-8 no mesmo filesystem do destino."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_file.write(content)
        return Path(temporary_file.name)


def _manifest_int(value: object, field_name: str, line_number: int) -> int:
    """Valida os inteiros exigidos pelo manifesto."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"Manifest line {line_number} field '{field_name}' must be an integer"
        )
    return value
