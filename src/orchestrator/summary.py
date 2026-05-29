"""Emissão do evento `execution_summary` ao fim de cada execução.

Decisão (vinda da fase discuss): uma única linha JSON no logger estruturado
existente (M0). Operadores grep-am `"event":"execution_summary"` no `.json`.

Nunca expõe conteúdo de `evidence`, prompts, respostas crus ou segredos —
só nomes de chaves de evidence e métricas agregadas.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any

from intelligence import get_cost_snapshot
from orchestrator.context import RoutineContext
from orchestrator.types import RoutineResult


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _duration_s(ctx: RoutineContext) -> float:
    return round((_now_utc() - ctx.started_at).total_seconds(), 3)


def _common_fields(ctx: RoutineContext, *, exit_code: int) -> dict[str, Any]:
    snap = get_cost_snapshot()
    return {
        "routine": ctx.routine_name,
        "duration_s": _duration_s(ctx),
        "tokens_in": snap.tokens_in,
        "tokens_out": snap.tokens_out,
        "cost_usd": round(snap.cost_usd, 4),
        "exit_code": exit_code,
        "dry_run": ctx.dry_run,
        "started_at": ctx.started_at.isoformat(),
        "finished_at": _now_utc().isoformat(),
    }


def emit(
    ctx: RoutineContext, *, result: RoutineResult, exit_code: int
) -> None:
    """Emite `execution_summary` no caminho de sucesso ou abort da rotina."""
    fields = _common_fields(ctx, exit_code=exit_code)
    fields["action"] = result.action.value
    fields["evidence_keys"] = sorted(result.evidence.keys())
    ctx.logger.info("execution_summary", **fields)


def emit_error(
    ctx: RoutineContext, *, error: BaseException, exit_code: int
) -> None:
    """Emite `execution_summary` quando a rotina lançou exceção."""
    fields = _common_fields(ctx, exit_code=exit_code)
    fields["action"] = "error"
    fields["error_type"] = type(error).__name__
    fields["error_msg"] = str(error)
    ctx.logger.info("execution_summary", **fields)


def emit_boot_failure(*, routine: str, error: BaseException, exit_code: int) -> None:
    """Fallback quando o logger ainda não está disponível.

    Escreve um JSON puro em stderr para que cron/agendadores tenham SEMPRE
    um registro estruturado, mesmo que o boot falhe antes do setup_logging.
    """
    payload = {
        "event": "execution_summary",
        "routine": routine,
        "action": "boot_error",
        "error_type": type(error).__name__,
        "error_msg": str(error),
        "exit_code": exit_code,
        "finished_at": _now_utc().isoformat(),
    }
    sys.stderr.write(json.dumps(payload) + "\n")
    sys.stderr.flush()


__all__ = ["emit", "emit_boot_failure", "emit_error"]
