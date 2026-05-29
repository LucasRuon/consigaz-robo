"""CLI do orquestrador. Despacha rotinas e mapeia exceções para exit codes."""

from __future__ import annotations

import argparse
import sys

from pydantic import ValidationError

from orchestrator import registry, summary
from orchestrator.boot import boot
from orchestrator.dispatch import dispatch
from orchestrator.exceptions import RoutineRegistryError, UnknownRoutineError
from platform_info import UnsupportedPlatformError

_EXIT_OK = 0
_EXIT_GENERIC_ERROR = 1
_EXIT_CONFIG_ERROR = 2
_EXIT_UNSUPPORTED_PLATFORM = 3
_EXIT_UNKNOWN_ROUTINE = 4
_EXIT_INTERRUPTED = 130


def build_parser() -> argparse.ArgumentParser:
    """Constrói o argparse do orquestrador."""
    parser = argparse.ArgumentParser(
        prog="consigaz-robo",
        description="Robô RPA híbrido (Desktop + Web) cross-platform.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--routine",
        type=str,
        default=None,
        help="Nome da rotina a executar (descoberta automática em src/routines/).",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="Lista rotinas registradas e sai com 0.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Propaga ctx.dry_run=True. Semântica: a rotina executa "
            "desktop+validação+LLM mas pula o submit web."
        ),
    )
    return parser


def _map_exception(err: BaseException) -> int:
    if isinstance(err, KeyboardInterrupt):
        return _EXIT_INTERRUPTED
    if isinstance(err, ValidationError):
        return _EXIT_CONFIG_ERROR
    if isinstance(err, UnsupportedPlatformError):
        return _EXIT_UNSUPPORTED_PLATFORM
    if isinstance(err, UnknownRoutineError | RoutineRegistryError):
        return _EXIT_UNKNOWN_ROUTINE
    return _EXIT_GENERIC_ERROR


def main(argv: list[str] | None = None) -> int:
    """Entry programático. Sem args → imprime help. Retorna exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as err:
        return int(err.code) if isinstance(err.code, int) else _EXIT_GENERIC_ERROR

    if args.list:
        registry.discover("routines")
        for name in registry.list_names():
            print(name)
        return _EXIT_OK

    if args.routine is None:
        parser.print_help()
        return _EXIT_OK

    # Boot — falha aqui aciona summary fallback (sem logger).
    try:
        boot_ctx = boot(routine=args.routine)
    except BaseException as err:
        exit_code = _map_exception(err)
        summary.emit_boot_failure(
            routine=args.routine, error=err, exit_code=exit_code
        )
        return exit_code

    # Discover + dispatch — pós-boot já temos logger; summary normal.
    try:
        registry.discover("routines")
        return dispatch(args.routine, boot_ctx, dry_run=args.dry_run)
    except BaseException as err:
        return _map_exception(err)
