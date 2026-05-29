"""Despacho de rotinas: resolve nome, reset M3, executa, emite summary."""

from __future__ import annotations

from intelligence import reset_for_new_execution
from intelligence.types import Action
from orchestrator import summary
from orchestrator.boot import BootContext
from orchestrator.context import RoutineContext
from orchestrator.registry import get as registry_get

_EXIT_OK = 0
_EXIT_ROUTINE_ABORT = 5


def _exit_for_action(action: Action) -> int:
    if action is Action.PROCEED_TO_WEB:
        return _EXIT_OK
    return _EXIT_ROUTINE_ABORT


def dispatch(name: str, boot_ctx: BootContext, *, dry_run: bool) -> int:
    """Resolve a rotina, executa-a e emite o `execution_summary`.

    Sequência:
      1. `registry.get(name)` (pode lançar `UnknownRoutineError` → CLI mapeia)
      2. `intelligence.reset_for_new_execution(settings)` ANTES da rotina
      3. Cria `RoutineContext` e executa
      4. Em sucesso: `summary.emit`; retorna exit code
      5. Em exceção da rotina: `summary.emit_error` → re-raise (CLI mapeia)
    """
    routine = registry_get(name)
    reset_for_new_execution(boot_ctx.settings)
    ctx = RoutineContext.from_boot(
        boot_ctx, dry_run=dry_run, routine_name=name
    )

    try:
        result = routine(ctx)
    except BaseException as err:
        summary.emit_error(ctx, error=err, exit_code=1)
        raise

    exit_code = (
        result.exit_code_hint
        if result.exit_code_hint is not None
        else _exit_for_action(result.action)
    )
    summary.emit(ctx, result=result, exit_code=exit_code)
    return exit_code


__all__ = ["dispatch"]
