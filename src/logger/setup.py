"""Setup do logging: pipeline structlog com saída dupla (.log humano + .json estruturado)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from logger.processors import DEFAULT_SENSITIVE_KEYS, make_sanitizer

_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def setup_logging(
    routine: str,
    log_dir: Path = Path("logs"),
    level: str = "INFO",
    sensitive_keys: frozenset[str] | None = None,
) -> None:
    """Configura structlog + handlers stdlib para logar em `.log` e `.json` no `log_dir`."""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    text_path = log_dir / f"{timestamp}_{routine}.log"
    json_path = log_dir / f"{timestamp}_{routine}.json"

    sanitizer = make_sanitizer(sensitive_keys or DEFAULT_SENSITIVE_KEYS)
    log_level = _LEVEL_MAP[level]

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        sanitizer,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )

    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)
    root.setLevel(log_level)

    text_handler = logging.FileHandler(text_path, encoding="utf-8")
    text_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=False),
            foreign_pre_chain=shared_processors,
        )
    )

    json_handler = logging.FileHandler(json_path, encoding="utf-8")
    json_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    )

    root.addHandler(text_handler)
    root.addHandler(json_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retorna logger structlog bound (use `get_logger(__name__)` nos módulos)."""
    return structlog.stdlib.get_logger(name)
