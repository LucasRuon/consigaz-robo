"""CLI do orquestrador. Despacha rotinas e mapeia exceções para exit codes."""

from __future__ import annotations

import argparse
import sys

from pydantic import ValidationError

from orchestrator.boot import boot
from platform_info import UnsupportedPlatformError

_EXIT_OK = 0
_EXIT_GENERIC_ERROR = 1
_EXIT_CONFIG_ERROR = 2
_EXIT_UNSUPPORTED_PLATFORM = 3


def build_parser() -> argparse.ArgumentParser:
    """Constrói o argparse do orquestrador."""
    parser = argparse.ArgumentParser(
        prog="consigaz-robo",
        description="Robô RPA híbrido (Desktop + Web) cross-platform.",
    )
    parser.add_argument(
        "--routine",
        type=str,
        default=None,
        help="Nome da rotina a executar (despacho real chega em M4).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa o boot mas não realiza efeitos (placeholder até M4).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry programático. Sem argv → imprime help. Retorna exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as err:
        return int(err.code) if isinstance(err.code, int) else _EXIT_GENERIC_ERROR

    if args.routine is None:
        parser.print_help()
        return _EXIT_OK

    try:
        boot(routine=args.routine)
    except ValidationError as err:
        print(f"erro de configuração: {err}", file=sys.stderr)
        return _EXIT_CONFIG_ERROR
    except UnsupportedPlatformError as err:
        print(f"plataforma não suportada: {err}", file=sys.stderr)
        return _EXIT_UNSUPPORTED_PLATFORM
    except Exception as err:
        print(f"falha inesperada: {err}", file=sys.stderr)
        return _EXIT_GENERIC_ERROR

    return _EXIT_OK
