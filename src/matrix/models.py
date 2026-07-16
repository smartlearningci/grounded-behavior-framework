"""Modelos de dados usados pela matriz de geração."""

from dataclasses import asdict, dataclass


@dataclass
class MatrixRow:
    """Representa exatamente uma linha da folha Matrix."""

    matrix_row_id: int
    batch_id: str
    chunk_id: str
    curriculum_level: str
    capability_code: str
    subskill_code: str
    subskill_name: str
    subskill_description: str
    domain: str
    document_style: str
    fact_type: str
    entity_type: str
    context_length: str
    fact_position: str
    distractor_type: str
    question_type: str
    language: str
    examples_per_prompt: int
    assigned_provider: str
    preferred_model: str
    prompt_version: str
    dataset_split_target: str
    generation_status: str
    output_file: str
    notes: str

    def to_dict(self) -> dict[str, object]:
        """Converte a linha num dicionário simples pela ordem dos campos."""
        return asdict(self)
