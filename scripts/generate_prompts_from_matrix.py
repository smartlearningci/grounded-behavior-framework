"""Gera prompts e metadados locais a partir da matriz de capacidades."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.matrix.reader import (  # noqa: E402
    ALLOWED_PROVIDERS,
    ALLOWED_STATUSES,
    read_matrix,
    validate_matrix_rows,
)
from src.prompts.writer import write_prompt_files, write_prompt_manifest  # noqa: E402


DEFAULT_MATRIX = "datasets/matrices/Capability_Matrix_N1_10000_v1.xlsx"
DEFAULT_OUTPUT_DIR = "prompts/generated/n1_v1"


def positive_integer(value: str) -> int:
    """Converte um argumento num inteiro estritamente positivo."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser da linha de comandos para geração local."""
    parser = argparse.ArgumentParser(
        description="Gera prompts rastreáveis a partir da folha Matrix.",
    )
    parser.add_argument("--matrix", default=DEFAULT_MATRIX)
    parser.add_argument("--sheet", default="Matrix")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--status",
        default="pending",
        choices=sorted(ALLOWED_STATUSES),
    )
    parser.add_argument("--provider", choices=sorted(ALLOWED_PROVIDERS))
    parser.add_argument("--limit", type=positive_integer)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Executa leitura, filtros, escrita dos pares e criação do manifesto."""
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        rows = read_matrix(arguments.matrix, sheet_name=arguments.sheet)
        validate_matrix_rows(rows)
        selected = rows
        if arguments.status is not None:
            selected = [
                row
                for row in selected
                if row.generation_status == arguments.status
            ]
        if arguments.provider is not None:
            selected = [
                row
                for row in selected
                if row.assigned_provider == arguments.provider
            ]
        if arguments.limit is not None:
            selected = selected[: arguments.limit]
        if not selected:
            raise ValueError("No matrix rows matched the selected filters")

        prompt_paths = write_prompt_files(
            selected,
            arguments.output_dir,
            overwrite=arguments.overwrite,
        )
        write_prompt_manifest(
            selected,
            arguments.output_dir,
            overwrite=arguments.overwrite,
        )
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    providers = ", ".join(sorted({row.assigned_provider for row in selected}))
    total_examples = sum(row.examples_per_prompt for row in selected)
    print(f"Linhas da matriz lidas: {len(rows)}")
    print(f"Linhas selecionadas: {len(selected)}")
    print(f"Prompts escritos: {len(prompt_paths)}")
    print(f"Diretório de saída: {Path(arguments.output_dir)}")
    print(f"Providers representados: {providers}")
    print(f"Total de exemplos pedidos: {total_examples}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
