"""Constrói prompts determinísticos a partir da matriz de capacidades."""

from src.matrix.models import MatrixRow


CONTEXT_LENGTHS = {
    "Short": "curto, com 3 a 5 frases",
    "Medium": "médio, com 6 a 10 frases",
    "Long": "longo, com 11 a 20 frases",
}
FACT_POSITIONS = {
    "Beginning": "no início do contexto",
    "Middle": "a meio do contexto",
    "End": "no fim do contexto",
}
DISTRACTOR_TYPES = {
    "D0_None": "não incluir distratores relevantes",
    "D1_Irrelevant": (
        "incluir informação irrelevante, sem alterar nem ocultar a resposta"
    ),
    "D2_SimilarFacts": (
        "incluir factos semelhantes que obriguem a selecionar o facto correto"
    ),
}
QUESTION_TYPES = {
    "Q1_Direct": "formular uma pergunta direta sobre o facto pretendido",
    "Q2_SpecificEntity": (
        "formular a pergunta identificando explicitamente a entidade pretendida"
    ),
    "Q3_Paraphrased": (
        "formular a pergunta por paráfrase, sem copiar literalmente o contexto"
    ),
}
DOCUMENT_STYLES = {
    "FAQ": "perguntas frequentes (FAQ)",
    "Institutional_Profile": "perfil institucional",
    "Notice": "aviso",
    "Service_Description": "descrição de serviço",
    "Short_Report": "relatório curto",
}
FACT_TYPES = {
    "Capacity": "capacidade",
    "Contact": "contacto",
    "Date": "data",
    "Duration": "duração",
    "Eligibility": "elegibilidade",
    "Frequency": "frequência",
    "Location": "localização",
    "Opening_Hours": "horário de funcionamento",
    "Price": "preço",
    "Purpose": "finalidade",
    "Quantity": "quantidade",
    "Requirement": "requisito",
    "Responsible": "responsável",
    "Status": "estado",
    "Time": "hora",
}
ENTITY_TYPES = {
    "Company": "empresa",
    "Department": "departamento",
    "Event": "evento",
    "Facility": "instalação",
    "Hotel": "hotel",
    "Library": "biblioteca",
    "Museum": "museu",
    "Office": "gabinete",
    "Organisation": "organização",
    "Programme": "programa",
    "Project": "projeto",
    "Route": "rota",
    "School": "escola",
    "Service": "serviço",
    "Species": "espécie",
}


def build_generation_prompt(row: MatrixRow) -> str:
    """Cria uma instrução pt-PT completa e reproduzível para uma linha."""
    context_length = _controlled_value(
        CONTEXT_LENGTHS,
        row.context_length,
        "context_length",
    )
    fact_position = _controlled_value(
        FACT_POSITIONS,
        row.fact_position,
        "fact_position",
    )
    distractor_type = _controlled_value(
        DISTRACTOR_TYPES,
        row.distractor_type,
        "distractor_type",
    )
    question_type = _controlled_value(
        QUESTION_TYPES,
        row.question_type,
        "question_type",
    )
    document_style = _controlled_value(
        DOCUMENT_STYLES,
        row.document_style,
        "document_style",
    )
    fact_type = FACT_TYPES.get(row.fact_type, _readable_label(row.fact_type))
    entity_type = ENTITY_TYPES.get(
        row.entity_type,
        _readable_label(row.entity_type),
    )

    return f"""
Gera exatamente {row.examples_per_prompt} exemplos em português europeu (pt-PT).

IDENTIFICAÇÃO DO CHUNK
- chunk: {row.chunk_id}
- nível curricular: {row.curriculum_level}
- capacidade: {row.capability_code}
- subskill: {row.subskill_code} — {row.subskill_name}
- objetivo da subskill: {row.subskill_description}

CARACTERÍSTICAS OBRIGATÓRIAS
- domínio: {row.domain}
- estilo do documento: {document_style}
- tipo de facto: {fact_type}
- tipo de entidade: {entity_type}
- extensão do contexto: {context_length}
- posição do facto: {fact_position}
- distratores: {distractor_type}
- tipo de pergunta: {question_type}
- idioma: {row.language}, com vocabulário e construções de português europeu

REGRAS
1. Produz exatamente {row.examples_per_prompt} exemplos distintos.
2. Cada exemplo deve conter apenas context, question e answer.
3. A resposta deve ser totalmente suportada pelo contexto fornecido.
4. Cada pergunta deve pedir apenas o facto pretendido para esta subskill.
5. Deve existir uma única resposta correta por exemplo.
6. Não uses conhecimento externo para completar a resposta.
7. Não repitas nem dupliques exemplos.
8. Usa sempre formulações naturais de português europeu (pt-PT).
9. Devolve apenas JSON válido, sem Markdown.
10. Não acrescentes explicações antes ou depois do JSON.

FORMATO DE SAÍDA OBRIGATÓRIO
{{
  "examples": [
    {{
      "context": "...",
      "question": "...",
      "answer": "..."
    }}
  ]
}}
""".strip()


def build_prompt_metadata(row: MatrixRow) -> dict[str, object]:
    """Seleciona os metadados de execução e rastreabilidade sem secrets."""
    return {
        "matrix_row_id": row.matrix_row_id,
        "batch_id": row.batch_id,
        "chunk_id": row.chunk_id,
        "curriculum_level": row.curriculum_level,
        "capability_code": row.capability_code,
        "subskill_code": row.subskill_code,
        "domain": row.domain,
        "assigned_provider": row.assigned_provider,
        "preferred_model": row.preferred_model,
        "prompt_version": row.prompt_version,
        "dataset_split_target": row.dataset_split_target,
        "examples_per_prompt": row.examples_per_prompt,
    }


def _controlled_value(
    mapping: dict[str, str],
    value: str,
    field_name: str,
) -> str:
    """Traduz um valor controlado ou rejeita valores desconhecidos."""
    try:
        return mapping[value]
    except KeyError as exc:
        raise ValueError(f"Unknown {field_name}: {value}") from exc


def _readable_label(value: str) -> str:
    """Converte um código livre em rótulo textual legível."""
    return value.replace("_", " ").strip().lower()
