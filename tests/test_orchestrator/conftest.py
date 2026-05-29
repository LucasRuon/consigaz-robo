"""Fixtures compartilhadas dos testes do orquestrador."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
import structlog

from intelligence import llm as llm_module
from orchestrator import registry as registry_module


@pytest.fixture
def clean_registry() -> Iterator[None]:
    """Garante registry vazio antes/depois do teste."""
    registry_module._clear()
    yield
    registry_module._clear()


@pytest.fixture
def reset_llm_state() -> Iterator[None]:
    llm_module._reset_client_for_tests()
    yield
    llm_module._reset_client_for_tests()


@pytest.fixture
def structlog_to_stdlib() -> Iterator[None]:
    """Faz logs do structlog cair no caplog (stdlib)."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    root = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
        )
    )
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    yield
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)
    structlog.reset_defaults()
