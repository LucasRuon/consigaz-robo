"""Camada de logging estruturado (structlog)."""
from logger.processors import DEFAULT_SENSITIVE_KEYS, MASK, make_sanitizer

__all__ = ["DEFAULT_SENSITIVE_KEYS", "MASK", "make_sanitizer"]
