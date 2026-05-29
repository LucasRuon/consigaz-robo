"""orchestrator — chassis de produção do robô.

Imports de submódulos primeiro garantem que `orchestrator.boot`,
`orchestrator.dispatch`, etc. continuem resolvíveis como módulos
(monkeypatch em testes legados depende disso).

API pública (re-exportada para conveniência):
    BootContext
    RoutineContext, RoutineResult, Routine
    register, get, list_names, discover
    RoutineRegistryError, RoutineNameError, UnknownRoutineError

Funções `boot()` e `dispatch()` ficam acessíveis como
`orchestrator.boot.boot` e `orchestrator.dispatch.dispatch` para
preservar o resolver de submódulos.
"""

from __future__ import annotations

from orchestrator import boot, dispatch  # preserva submódulos no namespace
from orchestrator.boot import BootContext
from orchestrator.context import RoutineContext
from orchestrator.exceptions import (
    RoutineNameError,
    RoutineRegistryError,
    UnknownRoutineError,
)
from orchestrator.registry import discover, get, list_names, register
from orchestrator.types import Routine, RoutineResult

__all__ = [
    "BootContext",
    "Routine",
    "RoutineContext",
    "RoutineNameError",
    "RoutineRegistryError",
    "RoutineResult",
    "UnknownRoutineError",
    "boot",
    "discover",
    "dispatch",
    "get",
    "list_names",
    "register",
]
