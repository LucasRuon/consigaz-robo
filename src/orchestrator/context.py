"""`RoutineContext`: DI imutável passado para cada rotina."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

from config import Settings
from logger.setup import get_logger
from platform_info import Platform

if TYPE_CHECKING:
    from orchestrator.boot import BootContext


@dataclass(frozen=True)
class RoutineContext:
    """Estado por-execução entregue à rotina.

    Frozen + sem campos mutáveis no shallow → todas as rotinas recebem a
    mesma "foto" do boot e não podem mexer no contexto global.
    """

    platform: Platform
    settings: Settings
    logger: structlog.stdlib.BoundLogger
    routine_name: str
    dry_run: bool
    started_at: datetime

    @classmethod
    def from_boot(
        cls,
        boot_ctx: BootContext,
        *,
        dry_run: bool,
        routine_name: str | None = None,
    ) -> RoutineContext:
        """Constrói a partir do `BootContext` e binda o logger com `routine=<nome>`."""
        name = routine_name or boot_ctx.routine
        bound_logger = get_logger(__name__).bind(routine=name)
        return cls(
            platform=boot_ctx.platform,
            settings=boot_ctx.settings,
            logger=bound_logger,
            routine_name=name,
            dry_run=dry_run,
            started_at=datetime.now(tz=UTC),
        )


__all__ = ["RoutineContext"]
