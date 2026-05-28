"""Processor structlog para mascarar valores de chaves consideradas sensíveis."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "password", "passwd", "secret", "token", "api_key",
    "apikey", "authorization", "cpf", "cnpj", "rg",
})

MASK: str = "***"

StructlogProcessor = Callable[[Any, str, dict[str, Any]], dict[str, Any]]


def make_sanitizer(
    sensitive_keys: frozenset[str] = DEFAULT_SENSITIVE_KEYS,
) -> StructlogProcessor:
    """Cria processor structlog que mascara valores de chaves sensíveis.

    Match é case-insensitive e por substring: se algum item de ``sensitive_keys``
    aparece como substring na chave normalizada (lower), o valor vira ``MASK``.

    Limitação (v1): não-recursivo. Dicts e listas aninhadas em valores NÃO são
    processados — apenas as chaves de primeiro nível do ``event_dict``.
    """
    def processor(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        return {
            k: (MASK if any(sk in k.lower() for sk in sensitive_keys) else v)
            for k, v in event_dict.items()
        }

    return processor
