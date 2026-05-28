"""Registry de schemas Pydantic referenciáveis por nome em prompts."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from intelligence.exceptions import SchemaNotRegisteredError

_REGISTRY: dict[str, type[BaseModel]] = {}


def register(name: str) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """Decorador: `@register("foo")` adiciona a classe ao registry."""

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        existing = _REGISTRY.get(name)
        if existing is not None and existing is not cls:
            raise RuntimeError(
                f"schema {name!r} já registrado para outra classe: {existing}"
            )
        _REGISTRY[name] = cls
        return cls

    return decorator


def get_schema(name: str) -> type[BaseModel]:
    """Retorna a classe registrada. Lança `SchemaNotRegisteredError` se ausente."""
    if name not in _REGISTRY:
        raise SchemaNotRegisteredError(name=name, known=sorted(_REGISTRY))
    return _REGISTRY[name]


def list_schemas() -> list[str]:
    """Lista nomes registrados em ordem estável."""
    return sorted(_REGISTRY)


def _clear_registry_for_tests() -> None:
    """Limpa o registry. Uso apenas em fixtures de teste."""
    _REGISTRY.clear()
