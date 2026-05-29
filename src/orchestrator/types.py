"""Tipos públicos do orquestrador: `RoutineResult` e alias `Routine`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from intelligence.types import Action

if TYPE_CHECKING:
    from orchestrator.context import RoutineContext


@dataclass(frozen=True)
class RoutineResult:
    """Retorno de uma rotina. Consumido por `dispatch` e `summary`."""

    action: Action
    evidence: dict[str, Any] = field(default_factory=dict)
    exit_code_hint: int | None = None


Routine = Callable[["RoutineContext"], RoutineResult]


__all__ = ["Routine", "RoutineResult"]
