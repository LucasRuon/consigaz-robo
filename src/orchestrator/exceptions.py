"""Exceções do orquestrador (separadas de `intelligence.exceptions`).

Domínios distintos: `intelligence` cuida de LLM/validação; `orchestrator`
cuida de despacho de rotinas. Herdar de uma base comum acoplaria as duas
camadas, então herdamos direto de `Exception`.
"""

from __future__ import annotations


class RoutineRegistryError(Exception):
    """Falha estrutural no registry (ex: nome duplicado em `@register`)."""


class RoutineNameError(RoutineRegistryError):
    """Nome de rotina inválido (regex `^[a-z][a-z0-9_-]*$`)."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Nome de rotina inválido: {name!r}")
        self.name = name


class UnknownRoutineError(Exception):
    """Rotina solicitada não está registrada."""

    def __init__(self, name: str, available: list[str] | None = None) -> None:
        avail = available or []
        msg = (
            f"rotina {name!r} não registrada — disponíveis: {avail}"
            if avail
            else f"rotina {name!r} não registrada (nenhuma rotina disponível)"
        )
        super().__init__(msg)
        self.name = name
        self.available = avail


__all__ = [
    "RoutineNameError",
    "RoutineRegistryError",
    "UnknownRoutineError",
]
