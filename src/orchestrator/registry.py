"""Registry de rotinas: decorator `@register` + descoberta automática.

Estado de módulo é OK — o orquestrador é single-process, single-execution.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from collections.abc import Callable

from logger.setup import get_logger
from orchestrator.exceptions import (
    RoutineNameError,
    RoutineRegistryError,
    UnknownRoutineError,
)
from orchestrator.types import Routine

_log = get_logger(__name__)
_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_REGISTRY: dict[str, Routine] = {}


def register(name: str) -> Callable[[Routine], Routine]:
    """Decorator que registra a rotina sob `name` no registry global."""
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
        raise RoutineNameError(name)

    def _decorator(fn: Routine) -> Routine:
        if name in _REGISTRY:
            raise RoutineRegistryError(f"nome {name!r} já registrado")
        _REGISTRY[name] = fn
        return fn

    return _decorator


def get(name: str) -> Routine:
    """Retorna rotina ou lança `UnknownRoutineError(available=...)`."""
    try:
        return _REGISTRY[name]
    except KeyError as err:
        raise UnknownRoutineError(name, available=list_names()) from err


def list_names() -> list[str]:
    """Nomes registrados em ordem alfabética."""
    return sorted(_REGISTRY)


def discover(package: str = "routines") -> None:
    """Importa todos os submódulos de `package`, disparando os `@register`.

    Falha de import em uma rotina é logada e ignorada — não derruba o resto.
    """
    try:
        pkg = importlib.import_module(package)
    except Exception as err:
        _log.warning(
            "routine_package_import_failed",
            package=package,
            error_type=type(err).__name__,
            error=str(err),
        )
        return

    pkg_path = getattr(pkg, "__path__", None)
    if pkg_path is None:
        return

    for _, mod_name, _ in pkgutil.iter_modules(pkg_path):
        full = f"{package}.{mod_name}"
        try:
            importlib.import_module(full)
        except Exception as err:
            _log.warning(
                "routine_import_failed",
                module=full,
                error_type=type(err).__name__,
                error=str(err),
            )


def _clear() -> None:
    """Limpa registry. Uso exclusivo de fixtures de teste."""
    _REGISTRY.clear()


__all__ = ["discover", "get", "list_names", "register"]
